# Instagram Publisher

`instagram-publisher` is a Claude/Codex skill for publishing Instagram content through the Instagram Graph API without using a browser. It supports photos, reels, and carousels from public URLs or local files, with captions, scheduling, user tags, alt text, comment controls, and setup guidance for first-time use.

The skill is designed for action requests such as "post this photo to Instagram", "schedule this reel", or "posta essa foto no ig". It intentionally skips adjacent tasks such as caption-only writing, hashtag research, analytics, content planning, and posting to other platforms.

## Skill Links

- GitHub: [augustoFranke/instagram-publisher](https://github.com/augustoFranke/instagram-publisher)
- Codex plugin: [View instagram-publisher](codex://plugins/instagram-publisher?marketplacePath=%2FUsers%2Faugustodoregofranke%2F.agents%2Fplugins%2Fmarketplace.json)
- Codex share link: [Share instagram-publisher](codex://plugins/instagram-publisher?marketplacePath=%2FUsers%2Faugustodoregofranke%2F.agents%2Fplugins%2Fmarketplace.json&mode=share)
- Claude plugin: `instagram-publisher@instagram-publisher`
- Claude marketplace path: `/Users/augustodoregofranke/.claude/plugins/marketplaces/instagram-publisher`

Install from the local Claude marketplace:

```bash
claude plugin install instagram-publisher@instagram-publisher
```

## What The Skill Does

- Publishes single-image posts with optional captions, alt text, user tags, scheduling, and disabled comments.
- Publishes reels from public video URLs or local video files, including optional cover image URLs.
- Publishes carousels with 2 to 10 image and/or video items.
- Serves local files through Tailscale Funnel so the Instagram Graph API can fetch them from a temporary HTTPS URL.
- Guides the assistant to offer caption help when the user did not provide a caption.
- Maps common API and environment failures to clear recovery steps.

## Repository Structure

```text
.
├── SKILL.md
├── publish.py
├── setup.md
├── .env.example
├── RETROSPECTIVA.md
└── eval/
    ├── eval_execution_results.json
    ├── eval_output.txt
    ├── eval_prompt.md
    ├── run_execution_eval.py
    ├── trigger_eval.json
    ├── eval.log
    └── run_loop.log
```

`SKILL.md` is the assistant-facing instruction file. Its frontmatter controls when the skill should trigger, and the body documents how to choose commands, flags, captions, local files, and error handling.

`publish.py` is the Python 3 command-line publisher. It uses only the standard library plus the local Tailscale CLI, and calls the Instagram Graph API directly.

`setup.md` is the user-facing setup guide for creating a Meta app, finding `IG_USER_ID`, generating a long-lived access token, creating `.env`, and enabling Tailscale Funnel for local files.

`RETROSPECTIVA.md` records the technical decisions, iterations, removed features, API findings, test notes, and eval history.

`eval/` contains execution and triggering evaluation artifacts. The primary machine-readable result is `eval/eval_execution_results.json`.

## Initial Setup

Install the skill in Claude Code:

```bash
mkdir -p ~/.claude/skills
cp -R instagram-publisher ~/.claude/skills/instagram-publisher
```

Install the skill in Codex:

```bash
mkdir -p ~/.codex/skills
cp -R instagram-publisher ~/.codex/skills/instagram-publisher
```

Create the environment file:

```bash
cp ~/.claude/skills/instagram-publisher/.env.example \
  ~/.claude/skills/instagram-publisher/.env
```

For Codex, create the same file under `~/.codex/skills/instagram-publisher/.env`.

Edit `.env` and provide:

```text
IG_USER_ID=<your numeric Instagram Business user ID>
ACCESS_TOKEN=<your long-lived Instagram Graph API access token>
```

The Instagram account must be a Professional account connected to a Facebook Page. The Meta app/token must include Instagram publishing permissions, especially `instagram_basic` and `instagram_content_publish`.

For local files, install and authenticate Tailscale, then enable Funnel for the machine. Public URL posts do not require Tailscale.

The detailed onboarding flow lives in `setup.md`.

## Usage

Photo from URL:

```bash
python3 ~/.claude/skills/instagram-publisher/publish.py photo \
  "https://example.com/photo.jpg" \
  --caption "Hello from the Graph API"
```

Photo from a local file:

```bash
python3 ~/.claude/skills/instagram-publisher/publish.py photo \
  --file /absolute/path/to/photo.jpg \
  --caption "Local upload"
```

Reel with thumbnail:

```bash
python3 ~/.claude/skills/instagram-publisher/publish.py reel \
  "https://example.com/video.mp4" \
  --cover-url "https://example.com/thumb.jpg" \
  --caption "Behind the scenes"
```

Carousel:

```bash
python3 ~/.claude/skills/instagram-publisher/publish.py carousel \
  "https://example.com/1.jpg" \
  "https://example.com/2.jpg" \
  "https://example.com/clip.mp4" \
  --caption "Swipe through"
```

## Architecture

The system has two layers:

1. The skill layer (`SKILL.md`) tells the assistant when to use the tool and how to translate user intent into a safe `publish.py` command.
2. The execution layer (`publish.py`) performs the actual API workflow against `https://graph.instagram.com/v25.0`.

For URL-based media, `publish.py` sends the media URL directly to the Instagram Graph API, creates a media container, polls until the container is ready, publishes it, and verifies the resulting permalink.

For local media, `publish.py` starts a temporary local HTTP server, exposes it with Tailscale Funnel, waits until the public HTTPS URL is reachable, hands that URL to Meta, then shuts the server and Funnel down after processing completes.

For carousels, the script creates child media containers first, then creates and publishes a parent carousel container using the child IDs.

Scheduling is implemented through `published=false` and `scheduled_publish_time` at publish time. The script enforces Instagram's scheduling window: at least 10 minutes in the future and at most 75 days ahead.

## Eval Results

The execution eval checks whether the skill produces the correct command or recovery response for representative user requests in English and Portuguese.

Latest execution eval:

- Date: 2026-05-22
- Cases: 10/10 passed
- Assertions: 38/38 passed
- Pass rate: 100%

Covered scenarios:

- Photo from URL with caption
- Photo from local file
- Reel with cover URL
- Scheduled photo
- Carousel from URLs
- Photo with user tags, alt text, and disabled comments
- Carousel from local files
- Reel from local file with disabled comments
- Expired token diagnosis
- No-caption behavior

Run the eval:

```bash
python3 eval/run_execution_eval.py
```

The script writes `eval/eval_execution_results.json` and prints a summary table.

Triggering eval artifacts are also kept in `eval/`. The retrospective notes that headless triggering evals were not a reliable primary metric for this action-oriented skill, but they were still useful for checking false positives and refining the frontmatter description.
