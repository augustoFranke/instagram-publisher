#!/usr/bin/env python3
# Instagram Graph API publisher — supports photo, reel, and carousel posts.

import argparse
import http.server
import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_BASE = "https://graph.instagram.com/v25.0"
TAILSCALE = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"


# ── Local file serving via Tailscale Funnel ──────────────────────────────────

def _free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _tailscale_hostname():
    result = subprocess.run(
        [TAILSCALE, "status", "--json"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return data["Self"]["DNSName"].rstrip(".")


@contextmanager
def serve_via_funnel(file_path):
    if not os.path.exists(file_path):
        sys.exit(f"Erro: arquivo não encontrado: {file_path}")
    filename = os.path.basename(file_path).replace(" ", "_")
    port = _free_port()

    tmpdir = tempfile.mkdtemp()
    shutil.copy2(file_path, os.path.join(tmpdir, filename))

    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(
        *a, directory=tmpdir, **kw
    )
    # silence HTTP server logs
    handler.log_message = lambda *_: None
    server = http.server.HTTPServer(("", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    funnel_proc = None
    try:
        print(f"==> Expondo {filename} via Tailscale Funnel (porta {port})...")
        # run in background — command blocks until Ctrl+C otherwise
        funnel_proc = subprocess.Popen(
            [TAILSCALE, "funnel", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        hostname = _tailscale_hostname()
        url = f"https://{hostname}/{filename}"
        print(f"    URL pública: {url}")

        # wait until the URL is actually reachable before handing it to Meta
        print("    Aguardando Funnel propagar...", end="", flush=True)
        for _ in range(24):  # up to 120s
            time.sleep(5)
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=5):
                    break
            except Exception:
                print(".", end="", flush=True)
        else:
            sys.exit(f"\nErro: Funnel não ficou acessível em 120s")
        print(" ok")

        yield url
    finally:
        if funnel_proc:
            funnel_proc.terminate()
            funnel_proc.wait()
        subprocess.run([TAILSCALE, "funnel", "reset"], capture_output=True)
        server.shutdown()
        shutil.rmtree(tmpdir, ignore_errors=True)
        print("    Funnel encerrado.")


# ── Meta Graph API helpers ────────────────────────────────────────────────────

def load_env():
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.exists(env_path):
        sys.exit(f"Erro: {env_path} não encontrado. Copie .env.example e preencha.")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    for var in ("IG_USER_ID", "ACCESS_TOKEN"):
        if not os.environ.get(var):
            sys.exit(f"Erro: {var} não definido no .env")


def api_request(endpoint, params=None, method="POST"):
    url = f"{API_BASE}/{endpoint}"
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url)
    else:
        data = urllib.parse.urlencode(params or {}).encode()
        req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            detail = json.loads(body)
        except json.JSONDecodeError:
            detail = body
        sys.exit(f"Erro API ({e.code}): {json.dumps(detail, indent=2)}")


def create_container(params):
    uid = os.environ["IG_USER_ID"]
    params["access_token"] = os.environ["ACCESS_TOKEN"]
    resp = api_request(f"{uid}/media", params)
    container_id = resp.get("id")
    if not container_id:
        sys.exit(f"Erro ao criar container: {resp}")
    return container_id


def poll_container(container_id, interval=5, timeout=120):
    token = os.environ["ACCESS_TOKEN"]
    elapsed = 0
    while elapsed < timeout:
        resp = api_request(
            container_id,
            {"fields": "status_code,status", "access_token": token},
            method="GET",
        )
        status = resp.get("status_code")
        print(f"    status: {status} ({elapsed}s)")
        if status == "FINISHED":
            return
        if status == "ERROR":
            sys.exit(f"Erro no processamento do container: {json.dumps(resp, indent=2)}")
        time.sleep(interval)
        elapsed += interval
    sys.exit(f"Timeout ({timeout}s) esperando container {container_id} ficar pronto")


def publish_container(container_id):
    uid = os.environ["IG_USER_ID"]
    resp = api_request(
        f"{uid}/media_publish",
        {"creation_id": container_id, "access_token": os.environ["ACCESS_TOKEN"]},
    )
    media_id = resp.get("id")
    if not media_id:
        sys.exit(f"Erro ao publicar: {resp}")
    return media_id


def parse_schedule(publish_time):
    # Returns dict with published + scheduled_publish_time to inject at container creation.
    from datetime import datetime, timezone
    dt = datetime.fromisoformat(publish_time)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    unix_ts = int(dt.timestamp())
    now = int(datetime.now(timezone.utc).timestamp())
    if unix_ts < now + 600:
        sys.exit("Erro: horário agendado deve ser pelo menos 10 minutos no futuro.")
    if unix_ts > now + 75 * 24 * 3600:
        sys.exit("Erro: horário agendado deve ser no máximo 75 dias no futuro.")
    return unix_ts


def verify(media_id):
    return api_request(
        media_id,
        {"fields": "permalink,timestamp", "access_token": os.environ["ACCESS_TOKEN"]},
        method="GET",
    )


def disable_comments(media_id):
    api_request(
        media_id,
        {"comment_enabled": "false", "access_token": os.environ["ACCESS_TOKEN"]},
    )
    print("    Comentários desativados.")


def add_common_params(params, args):
    if args.caption:
        params["caption"] = args.caption
    if args.user_tags:
        params["user_tags"] = args.user_tags


def _finish(args, container_id):
    if args.schedule:
        unix_ts = parse_schedule(args.schedule)
        uid = os.environ["IG_USER_ID"]
        resp = api_request(
            f"{uid}/media_publish",
            {
                "creation_id": container_id,
                "published": "false",
                "scheduled_publish_time": str(unix_ts),
                "access_token": os.environ["ACCESS_TOKEN"],
            },
        )
        media_id = resp.get("id")
        if not media_id:
            sys.exit(f"Erro ao agendar: {resp}")
        print(f"    media_id: {media_id}")
        # verify — scheduled posts don't have permalink yet
        info = api_request(
            media_id,
            {"fields": "timestamp,permalink", "access_token": os.environ["ACCESS_TOKEN"]},
            method="GET",
        )
        if info.get("permalink"):
            print(f"    permalink: {info.get('permalink')} (publicado imediatamente — scheduling não suportado neste modo)")
        print(f"\nAgendado para: {args.schedule} (UTC)")
        return
    media_id = publish_container(container_id)
    print(f"    media_id: {media_id}")
    if args.disable_comments:
        disable_comments(media_id)
    info = verify(media_id)
    print(f"    permalink: {info.get('permalink')}")
    print(f"    timestamp: {info.get('timestamp')}")
    print("\nPublicado com sucesso!")


# ── Subcommands ───────────────────────────────────────────────────────────────

def cmd_photo(args):
    print("==> Publicando foto...")

    def _run(url):
        params = {"image_url": url}
        add_common_params(params, args)
        if args.alt_text:
            params["alt_text"] = args.alt_text
        container_id = create_container(params)
        print(f"    container: {container_id}")
        print("==> Aguardando processamento...")
        poll_container(container_id)
        _finish(args, container_id)

    if args.file:
        with serve_via_funnel(args.file) as url:
            _run(url)
    elif args.url:
        _run(args.url)
    else:
        sys.exit("Erro: forneça uma URL (url) ou um arquivo local (--file PATH)")


def cmd_reel(args):
    print("==> Publicando reel...")

    def _run(url):
        params = {"media_type": "REELS", "video_url": url}
        add_common_params(params, args)
        if args.cover_url:
            params["cover_url"] = args.cover_url
        container_id = create_container(params)
        print(f"    container: {container_id}")
        print("==> Aguardando processamento do vídeo...")
        poll_container(container_id, timeout=300)
        _finish(args, container_id)

    if args.file:
        with serve_via_funnel(args.file) as url:
            _run(url)
    elif args.url:
        _run(args.url)
    else:
        sys.exit("Erro: forneça uma URL (url) ou um arquivo local (--file PATH)")


def cmd_carousel(args):
    file_list = getattr(args, "files", [])

    if file_list:
        funnels = []
        # open all funnels sequentially — each gets a unique port/path
        # we need all URLs before creating containers, so we stack context managers
        def _run_with_funnels(file_list, urls):
            if file_list:
                with serve_via_funnel(file_list[0]) as url:
                    _run_with_funnels(file_list[1:], urls + [url])
            else:
                _do_carousel(args, urls)
        _run_with_funnels(file_list, [])
    else:
        urls = args.urls or []
        if len(urls) < 2:
            sys.exit("Erro: carrossel precisa de pelo menos 2 itens.")
        if len(urls) > 10:
            sys.exit("Erro: carrossel suporta no máximo 10 itens.")
        _do_carousel(args, urls)


def _do_carousel(args, urls):
    if len(urls) < 2:
        sys.exit("Erro: carrossel precisa de pelo menos 2 itens.")
    if len(urls) > 10:
        sys.exit("Erro: carrossel suporta no máximo 10 itens.")

    print(f"==> Publicando carrossel ({len(urls)} itens)...")
    children_ids = []
    for i, url in enumerate(urls):
        params = {"is_carousel_item": "true", "access_token": os.environ["ACCESS_TOKEN"]}
        if url.endswith((".mp4", ".mov")):
            params["media_type"] = "VIDEO"
            params["video_url"] = url
        else:
            params["image_url"] = url
            if args.alt_text:
                params["alt_text"] = args.alt_text
        uid = os.environ["IG_USER_ID"]
        resp = api_request(f"{uid}/media", params)
        child_id = resp.get("id")
        if not child_id:
            sys.exit(f"Erro no item {i+1}: {resp}")
        print(f"    item {i+1}: {child_id}")
        children_ids.append(child_id)

    params = {"media_type": "CAROUSEL", "children": ",".join(children_ids)}
    add_common_params(params, args)
    container_id = create_container(params)
    print(f"    carousel container: {container_id}")
    print("==> Aguardando processamento...")
    poll_container(container_id)
    _finish(args, container_id)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Instagram Graph API Publisher")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--caption", default="")
    common.add_argument("--alt-text", default="")
    common.add_argument("--user-tags", default="")
    common.add_argument("--disable-comments", action="store_true")
    common.add_argument("--schedule", default="", metavar="DATETIME",
                        help="ISO 8601 UTC, mín 10min no futuro. Ex: '2026-05-22T15:00:00'")

    p_photo = sub.add_parser("photo", parents=[common])
    p_photo.add_argument("url", nargs="?", default="", help="URL pública da imagem")
    p_photo.add_argument("--file", default="", metavar="PATH", help="Arquivo local (serve via Tailscale Funnel)")

    p_reel = sub.add_parser("reel", parents=[common])
    p_reel.add_argument("url", nargs="?", default="", help="URL pública do vídeo (5-90s)")
    p_reel.add_argument("--file", default="", metavar="PATH", help="Arquivo local (serve via Tailscale Funnel)")
    p_reel.add_argument("--cover-url", default="")

    p_carousel = sub.add_parser("carousel", parents=[common])
    p_carousel.add_argument("urls", nargs="*", help="URLs públicas (2-10 itens)")
    p_carousel.add_argument("--files", nargs="+", default=[], metavar="PATH",
                            help="Arquivos locais (serve via Tailscale Funnel)")

    args = parser.parse_args()
    load_env()

    {"photo": cmd_photo, "reel": cmd_reel, "carousel": cmd_carousel}[args.command](args)


if __name__ == "__main__":
    main()
