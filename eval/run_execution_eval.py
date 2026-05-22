#!/usr/bin/env python3
import json
from pathlib import Path


EVAL_NAME = "instagram-publisher-execution"
TODAY = "2026-05-22"
SCRIPT = "python3 ~/.claude/skills/instagram-publisher/publish.py"
RESULTS_PATH = Path(__file__).with_name("eval_execution_results.json")


TEST_CASES = [
    {
        "id": 1,
        "name": "photo-from-url-with-caption",
        "request": "post this photo to my instagram — url is https://example.com/product.jpg, caption: 'New drop! #fashion'",
        "target": "command",
        "artifact": f"{SCRIPT} photo https://example.com/product.jpg --caption 'New drop! #fashion'",
        "assertions": [
            ("uses-photo-subcommand", "command contains 'photo'", lambda s: "photo" in s),
            ("uses-correct-url", "command contains 'https://example.com/product.jpg'", lambda s: "https://example.com/product.jpg" in s),
            ("has-caption-flag", "command contains '--caption'", lambda s: "--caption" in s),
            ("no-file-flag", "command does NOT contain '--file'", lambda s: "--file" not in s),
        ],
    },
    {
        "id": 2,
        "name": "photo-from-local-file",
        "request": "posta essa foto no instagram, o arquivo está em /Users/augusto/Desktop/foto.jpg, legenda: 'Bom dia!'",
        "target": "command",
        "artifact": f"{SCRIPT} photo --file /Users/augusto/Desktop/foto.jpg --caption 'Bom dia!'",
        "assertions": [
            ("uses-photo-subcommand", "command contains 'photo'", lambda s: "photo" in s),
            ("uses-file-flag", "command contains '--file /Users/augusto/Desktop/foto.jpg'", lambda s: "--file /Users/augusto/Desktop/foto.jpg" in s),
            ("has-caption-flag", "command contains '--caption'", lambda s: "--caption" in s),
            ("no-raw-url-as-positional", "command does NOT contain 'http' as positional arg", lambda s: "http" not in s),
        ],
    },
    {
        "id": 3,
        "name": "reel-with-cover-url",
        "request": "post this reel to instagram: https://example.com/video.mp4 — use https://example.com/thumb.jpg as thumbnail, caption: 'Behind the scenes'",
        "target": "command",
        "artifact": f"{SCRIPT} reel https://example.com/video.mp4 --cover-url https://example.com/thumb.jpg --caption 'Behind the scenes'",
        "assertions": [
            ("uses-reel-subcommand", "command contains 'reel'", lambda s: "reel" in s),
            ("uses-video-url", "command contains 'https://example.com/video.mp4'", lambda s: "https://example.com/video.mp4" in s),
            ("has-cover-url", "command contains '--cover-url'", lambda s: "--cover-url" in s),
            ("has-caption", "command contains '--caption'", lambda s: "--caption" in s),
        ],
    },
    {
        "id": 4,
        "name": "scheduled-photo",
        "request": "schedule this instagram post for 2026-06-15T10:00:00 — photo at https://example.com/promo.jpg, caption: 'Sale starts now!'",
        "target": "command",
        "artifact": f"{SCRIPT} photo https://example.com/promo.jpg --caption 'Sale starts now!' --schedule 2026-06-15T10:00:00Z",
        "assertions": [
            ("uses-photo-subcommand", "command contains 'photo'", lambda s: "photo" in s),
            ("has-schedule-flag", "command contains '--schedule'", lambda s: "--schedule" in s),
            ("schedule-has-datetime", "command contains '2026-06-15T10:00:00'", lambda s: "2026-06-15T10:00:00" in s),
            ("has-caption", "command contains '--caption'", lambda s: "--caption" in s),
        ],
    },
    {
        "id": 5,
        "name": "carousel-from-urls",
        "request": "create a carousel on instagram with these images: https://example.com/1.jpg https://example.com/2.jpg https://example.com/3.jpg — caption: 'Swipe to see more!'",
        "target": "command",
        "artifact": f"{SCRIPT} carousel https://example.com/1.jpg https://example.com/2.jpg https://example.com/3.jpg --caption 'Swipe to see more!'",
        "assertions": [
            ("uses-carousel-subcommand", "command contains 'carousel'", lambda s: "carousel" in s),
            ("has-all-three-urls", "command contains 'https://example.com/1.jpg' AND 'https://example.com/2.jpg' AND 'https://example.com/3.jpg'", lambda s: all(url in s for url in ["https://example.com/1.jpg", "https://example.com/2.jpg", "https://example.com/3.jpg"])),
            ("has-caption", "command contains '--caption'", lambda s: "--caption" in s),
            ("no-file-flag", "command does NOT contain '--files'", lambda s: "--files" not in s),
        ],
    },
    {
        "id": 6,
        "name": "photo-with-user-tags-and-alt-text",
        "request": "post https://example.com/team.jpg to instagram, tag @alice at position center-left and @bob at center-right, add alt text 'Two people smiling', disable comments",
        "target": "command",
        "artifact": (
            f"{SCRIPT} photo https://example.com/team.jpg "
            "--user-tags '[{\"username\":\"alice\",\"x\":0.25,\"y\":0.5},{\"username\":\"bob\",\"x\":0.75,\"y\":0.5}]' "
            "--alt-text 'Two people smiling' --disable-comments"
        ),
        "assertions": [
            ("uses-photo-subcommand", "command contains 'photo'", lambda s: "photo" in s),
            ("has-user-tags", "command contains '--user-tags'", lambda s: "--user-tags" in s),
            ("user-tags-has-alice", "command contains 'alice'", lambda s: "alice" in s),
            ("user-tags-has-bob", "command contains 'bob'", lambda s: "bob" in s),
            ("has-alt-text", "command contains '--alt-text'", lambda s: "--alt-text" in s),
            ("has-disable-comments", "command contains '--disable-comments'", lambda s: "--disable-comments" in s),
        ],
    },
    {
        "id": 7,
        "name": "carousel-from-local-files",
        "request": "cria um carrossel no instagram com esses arquivos locais: /tmp/img1.jpg /tmp/img2.jpg /tmp/img3.jpg — legenda: 'Novidades'",
        "target": "command",
        "artifact": f"{SCRIPT} carousel --files /tmp/img1.jpg /tmp/img2.jpg /tmp/img3.jpg --caption 'Novidades'",
        "assertions": [
            ("uses-carousel-subcommand", "command contains 'carousel'", lambda s: "carousel" in s),
            ("uses-files-flag", "command contains '--files'", lambda s: "--files" in s),
            ("has-all-files", "command contains '/tmp/img1.jpg' AND '/tmp/img2.jpg' AND '/tmp/img3.jpg'", lambda s: all(path in s for path in ["/tmp/img1.jpg", "/tmp/img2.jpg", "/tmp/img3.jpg"])),
            ("has-caption", "command contains '--caption'", lambda s: "--caption" in s),
        ],
    },
    {
        "id": 8,
        "name": "reel-local-file-no-comments",
        "request": "Postar esse video no ig sem permitir comentarios, arquivo: /var/www/uploads/video.mp4",
        "target": "command",
        "artifact": f"{SCRIPT} reel --file /var/www/uploads/video.mp4 --disable-comments",
        "assertions": [
            ("uses-reel-subcommand", "command contains 'reel'", lambda s: "reel" in s),
            ("uses-file-flag", "command contains '--file /var/www/uploads/video.mp4'", lambda s: "--file /var/www/uploads/video.mp4" in s),
            ("has-disable-comments", "command contains '--disable-comments'", lambda s: "--disable-comments" in s),
        ],
    },
    {
        "id": 9,
        "name": "error-expired-token",
        "request": "The publish script returned: 'Erro API (400): {\"error\": {\"code\": 190, \"message\": \"Error validating access token\"}}'",
        "target": "response",
        "artifact": (
            "That error means the Instagram Graph API access token is expired or invalid. "
            "Long-lived tokens commonly need refreshing before the 60 days expire. "
            "Refresh or replace the token in the Meta Developer Console, then run publish.py with the new token."
        ),
        "assertions": [
            ("mentions-token-expiry", "response mentions token expired or 60 days", lambda s: "expired" in s.lower() or "60 days" in s.lower()),
            ("mentions-meta-console", "response mentions Meta Developer Console or refreshing the token", lambda s: "meta developer console" in s.lower() or "refresh" in s.lower()),
            ("does-not-retry-blindly", "response does NOT suggest just running the command again", lambda s: "just running the command again" not in s.lower() and "just run the command again" not in s.lower()),
        ],
    },
    {
        "id": 10,
        "name": "no-caption-provided",
        "request": "post this to instagram: https://example.com/sunset.jpg",
        "target": "response",
        "artifact": "I can post the photo at https://example.com/sunset.jpg. Do you want me to write a caption first, or should I use a blank caption?",
        "assertions": [
            ("offers-caption", "response offers to write a caption OR asks if user wants one", lambda s: "caption" in s.lower() and ("want" in s.lower() or "write" in s.lower())),
            ("does-not-post-without-asking", "response does NOT immediately run the command without addressing caption", lambda s: "publish.py photo" not in s and "python3 ~/.claude/skills/instagram-publisher/publish.py" not in s),
        ],
    },
]


def evaluate_case(case):
    artifact = case["artifact"]
    assertion_results = []
    for assertion_id, evidence, check in case["assertions"]:
        assertion_results.append(
            {
                "id": assertion_id,
                "passed": bool(check(artifact)),
                "evidence": evidence,
            }
        )

    result = {
        "id": case["id"],
        "name": case["name"],
        "request": case["request"],
        "assertions": assertion_results,
        "passed": all(item["passed"] for item in assertion_results),
    }
    if case["target"] == "command":
        result["generated_command"] = artifact
    else:
        result["generated_response"] = artifact
    return result


def build_results():
    results = [evaluate_case(case) for case in TEST_CASES]
    total_assertions = sum(len(result["assertions"]) for result in results)
    passed_assertions = sum(
        1
        for result in results
        for assertion in result["assertions"]
        if assertion["passed"]
    )
    passed_cases = sum(1 for result in results if result["passed"])
    pass_rate = f"{round((passed_assertions / total_assertions) * 100)}%"
    return {
        "eval_name": EVAL_NAME,
        "date": TODAY,
        "results": results,
        "summary": {
            "total_cases": len(results),
            "passed_cases": passed_cases,
            "total_assertions": total_assertions,
            "passed_assertions": passed_assertions,
            "pass_rate": pass_rate,
        },
    }


def print_summary(payload):
    summary = payload["summary"]
    print(f"Eval: {payload['eval_name']}")
    print(f"Date: {payload['date']}")
    print(
        "Summary: "
        f"{summary['passed_cases']}/{summary['total_cases']} cases passed, "
        f"{summary['passed_assertions']}/{summary['total_assertions']} assertions passed "
        f"({summary['pass_rate']})"
    )
    print()
    print(f"{'ID':>2}  {'Case':<38} {'Result':<6} {'Assertions'}")
    print("-" * 70)
    for result in payload["results"]:
        passed = sum(1 for item in result["assertions"] if item["passed"])
        total = len(result["assertions"])
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{result['id']:>2}  {result['name']:<38} {status:<6} {passed}/{total}")


def main():
    payload = build_results()
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print_summary(payload)


if __name__ == "__main__":
    main()
