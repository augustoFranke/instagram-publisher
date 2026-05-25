# Instagram Publisher

`instagram-publisher` is a Claude/Codex skill for publishing Instagram content through the Instagram Graph API without using a browser. It supports photos, reels, and carousels from public URLs or local files, with captions, scheduling, user tags, alt text, comment controls, and setup guidance for first-time use.

The skill is designed for action requests such as "post this photo to Instagram", "schedule this reel", or "posta essa foto no ig". It intentionally skips adjacent tasks such as caption-only writing, hashtag research, analytics, content planning, and posting to other platforms.

## Skill Links

- GitHub: [augustoFranke/instagram-publisher](https://github.com/augustoFranke/instagram-publisher)

Install via `npx skills` (Easiest, works for Claude Code, Cursor, and 50+ other agents):

```bash
npx skills add augustoFranke/instagram-publisher
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

### 1. Install the Skill
The recommended way to install `instagram-publisher` is via `npx skills`:

```bash
npx skills add augustoFranke/instagram-publisher
```

This will download the skill to `~/.agents/skills/instagram-publisher/` and automatically register/link the `SKILL.md` file with your AI coding agents (such as Claude Code, Cursor, Windsurf, etc.).

If you prefer a manual installation instead, clone the repo and copy the files to your agent's skill directory:

```bash
git clone https://github.com/augustoFranke/instagram-publisher.git
mkdir -p ~/.claude/skills/instagram-publisher
cp instagram-publisher/publish.py instagram-publisher/SKILL.md instagram-publisher/setup.md instagram-publisher/.env.example ~/.claude/skills/instagram-publisher/
```

### 2. Configure Credentials
Create a `.env` file in the installed skill directory (e.g. `~/.agents/skills/instagram-publisher/` if installed via `npx skills`, or `~/.claude/skills/instagram-publisher/` for manual install):

```bash
# If installed via npx skills:
cp ~/.agents/skills/instagram-publisher/.env.example ~/.agents/skills/instagram-publisher/.env

# If manually installed to Claude Code:
cp ~/.claude/skills/instagram-publisher/.env.example ~/.claude/skills/instagram-publisher/.env
```

Edit `.env` and provide:

```text
IG_USER_ID=<your numeric Instagram Business user ID>
ACCESS_TOKEN=<your long-lived Instagram Graph API access token>
```

The Instagram account must be a Professional account connected to a Facebook Page. The Meta app/token must include Instagram publishing permissions, especially `instagram_basic` and `instagram_content_publish`.

For local files, install and authenticate Tailscale, then enable Funnel for the machine. Public URL posts do not require Tailscale.

The detailed onboarding flow lives in [setup.md](setup.md).

## Usage

Once the skill is installed, **you do not need to run the Python script yourself**. Simply ask your AI coding agent (e.g. Claude Code) in natural language to publish or schedule content for you. 

Here are representative examples of how to interact with your agent:

### Publish a Photo
> **User:** "Post this photo to Instagram: https://example.com/photo.jpg with the caption 'Hello from the Graph API!'"
> 
> *The agent will automatically translate this request into the correct script arguments, run the publisher in the background, and return the published post's permalink.*

### Publish a Local File
> **User:** "Post my local photo /absolute/path/to/photo.jpg to Instagram with the caption 'Local upload'"

### Publish a Reel
> **User:** "Post a reel using the video https://example.com/video.mp4, cover thumbnail https://example.com/thumb.jpg, and caption 'Behind the scenes'"

### Publish a Carousel (Swipe Post)
> **User:** "Create a carousel post with these three items: https://example.com/1.jpg, https://example.com/2.jpg, and https://example.com/clip.mp4. Use the caption 'Swipe through!'"

### Schedule a Post
> **User:** "Schedule this photo https://example.com/photo.jpg for next Monday at 15:00 UTC with the caption 'Coming soon!'"


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
