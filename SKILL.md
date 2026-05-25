---
name: instagram-publisher
description: "Publish photos, videos, and carousels to Instagram via the Graph API — no browser needed. Use when the user wants to upload media they have (local file, URL, or attachment) to Instagram/IG/insta — in English (post/publish/share/schedule) or Portuguese (postar/publicar/agendar no Instagram/ig). Handles captions, scheduling, user tags, alt text, comment controls. Skip: caption writing only, hashtag research, analytics, content planning, or posting to other platforms."
---

# Instagram Publisher

Publishes photos, reels, and carousels via the Instagram Graph API.

Script path:
- Claude Code / general symlink: `~/.claude/skills/instagram-publisher/publish.py`
- npx skills (global store): `~/.agents/skills/instagram-publisher/publish.py`

Use the script path for the host you are running inside. If installed via `npx skills` in other agents, search for the script in the global store path.

## First-run setup check (always run this before anything else)

Before doing anything the user asked, run these checks in order and resolve any issues interactively:

### 1. Credentials

Check the `.env` for the active install path:

- Claude Code: `~/.claude/skills/instagram-publisher/.env`
- npx skills (global store): `~/.agents/skills/instagram-publisher/.env`

```bash
cat ~/.claude/skills/instagram-publisher/.env 2>/dev/null
```

- If the file is **missing** or either `IG_USER_ID` / `ACCESS_TOKEN` is empty or still contains a placeholder (`<...>`):
  - Tell the user setup is needed.
  - Read `setup.md` and walk them through Steps 1–4 interactively, one step at a time.
  - After they provide both values, write them to `.env` and confirm.

### 2. Tailscale Funnel (only needed for local files — skip if posting from URLs only)

Check Tailscale status:

```bash
tailscale version 2>/dev/null && tailscale funnel status 2>/dev/null
```

- If `tailscale` is **not installed**: tell the user and walk them through setup.md Step 5.
- If Tailscale is installed but **not logged in** (`tailscale status` shows "not logged in"): instruct the user to run `! tailscale up`.
- If Funnel is **not enabled** (status shows an error or no funnel entries): walk them through the ACL policy change in setup.md Step 5.
- Only proceed once `tailscale funnel status` exits cleanly.

> If the user explicitly says they'll only post from URLs (not local files), skip the Tailscale check.

### 3. Ready confirmation

Once both checks pass, confirm: "You're all set — credentials and Tailscale are configured." Then proceed with what the user originally asked.

## Choosing the content type

| Type | When to use |
|---|---|
| `photo` | Single image (JPEG, PNG, WebP) |
| `reel` | Short video — H.264 video, AAC audio, 5–90 s |
| `carousel` | 2–10 images **and/or videos** in one post |

## Caption guidance

- If the user didn't provide a caption, **offer to write one** based on the content or context before posting.
- Instagram limit: **2,200 characters**, **30 hashtags** max. Trim or warn if exceeded.
- Multi-line captions in bash require `$'...\n...'` syntax:
  ```bash
  --caption $'First line\n\nSecond line #hashtag'
  ```

## Running the script

```bash
# Photo from URL
python3 ~/.claude/skills/instagram-publisher/publish.py photo "https://example.com/photo.jpg" \
  --caption "Hello! #test"

# Photo from local file
python3 ~/.claude/skills/instagram-publisher/publish.py photo \
  --file /absolute/path/to/photo.jpg --caption "Hello!"

# Reel from URL
python3 ~/.claude/skills/instagram-publisher/publish.py reel "https://example.com/video.mp4" \
  --caption "Check this out!"

# Reel from local file with custom thumbnail
python3 ~/.claude/skills/instagram-publisher/publish.py reel \
  --file /path/to/video.mp4 --cover-url "https://example.com/thumb.jpg" \
  --caption "My reel"

# Carousel — images and/or videos (mix supported: .mp4/.mov items are sent as VIDEO)
python3 ~/.claude/skills/instagram-publisher/publish.py carousel \
  "https://example.com/img1.jpg" "https://example.com/video.mp4" "https://example.com/img2.jpg" \
  --caption "Swipe through!"

# Carousel from local files
python3 ~/.claude/skills/instagram-publisher/publish.py carousel \
  --files /path/img1.jpg /path/clip.mp4 /path/img2.jpg \
  --caption "Swipe!"
```

## Optional flags

**All content types:**

| Flag | Description |
|---|---|
| `--caption TEXT` | Caption — hashtags and @mentions supported |
| `--user-tags JSON` | Tag users on the post (see format below) |
| `--disable-comments` | Lock comments after publishing |
| `--schedule DATETIME` | Schedule instead of posting immediately (ISO 8601 UTC, min 10 min ahead, max 75 days) |

**Photo and carousel only:**

| Flag | Description |
|---|---|
| `--alt-text TEXT` | Accessibility description for the image(s) |

**Reel only:**

| Flag | Description |
|---|---|
| `--cover-url URL` | Custom thumbnail image URL |

### User tags format

`x` and `y` are normalized coordinates (0.0–1.0) for where the tag pin appears on the image:

```bash
# Single tag
--user-tags '[{"username":"alice","x":0.3,"y":0.4}]'

# Multiple tags
--user-tags '[{"username":"alice","x":0.2,"y":0.5},{"username":"bob","x":0.7,"y":0.5}]'
```

### Full example with advanced flags

```bash
# Photo with alt text, user tags, comments disabled
python3 ~/.claude/skills/instagram-publisher/publish.py photo "https://example.com/photo.jpg" \
  --caption $'Launch day! 🚀 #startup\n\nLink in bio.' \
  --alt-text "Three people celebrating in front of a product launch banner" \
  --user-tags '[{"username":"alice","x":0.3,"y":0.4},{"username":"bob","x":0.7,"y":0.4}]' \
  --disable-comments

# Scheduled reel with custom thumbnail
python3 ~/.claude/skills/instagram-publisher/publish.py reel "https://example.com/video.mp4" \
  --caption "Behind the scenes 🎬" \
  --cover-url "https://example.com/thumb.jpg" \
  --schedule "2026-06-01T09:00:00"
```

## Local files (Tailscale Funnel)

Use `--file PATH` (photo/reel) or `--files PATH...` (carousel) for local files. The script serves the file via Tailscale Funnel so Instagram can fetch it over HTTPS.

Requirements: Tailscale installed, authenticated, and Funnel enabled. If the user hasn't set this up, refer them to `setup.md`.

## After publishing

Report back:
- **permalink** of the published post, or
- **scheduled time** if `--schedule` was used.

## Error handling

Read the script's output carefully if something fails:

| Error pattern | Likely cause | What to tell the user |
|---|---|---|
| `Error: IG_USER_ID not set` / `ACCESS_TOKEN not set` | Missing `.env` | Open `setup.md` and follow Step 2 |
| API error `190` / `invalid token` / `401` | Token expired (long-lived tokens last 60 days) | Refresh the token via Meta Developer Console and update `.env` |
| API error `352` / `unsupported format` | Wrong video codec | Re-encode to H.264 + AAC |
| API error `36000` / caption too long | Caption over 2,200 chars | Shorten the caption |
| `Funnel not reachable in 120s` | Tailscale Funnel not enabled | Check Tailscale auth and Funnel setup in `setup.md` |
| `File not found` | Wrong path | Confirm the absolute path exists |
