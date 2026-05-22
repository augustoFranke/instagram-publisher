# Instagram Publisher — Execution Eval

You are evaluating whether the instagram-publisher skill produces the correct `publish.py` command for each user request below.

## Your task

For each test case:
1. Read the user request
2. Decide what `publish.py` command should be constructed based on the SKILL.md instructions
3. Write the command to the results file
4. Run the assertions programmatically

Save all results to `/Users/augustodoregofranke/Developer/instagram-publisher-workspace/eval_execution_results.json`

Then print a summary to stdout.

---

## SKILL.md (full content — use this as your reference)

```
Script path: ~/.claude/skills/instagram-publisher/publish.py

Content types:
- photo: single image (JPEG, PNG, WebP)
- reel: short video, H.264 + AAC, 5-90s
- carousel: 2-10 images and/or videos

Flags (all types): --caption TEXT, --user-tags JSON, --disable-comments, --schedule DATETIME
Flags (photo+carousel only): --alt-text TEXT
Flags (reel only): --cover-url URL

Local files: use --file PATH for photo/reel, --files PATH... for carousel
URLs: pass as positional argument after the content type

user-tags format: '[{"username":"handle","x":0.5,"y":0.3}]'  (x,y are 0.0-1.0 normalized coords)
schedule format: ISO 8601 UTC, min 10 minutes in future

Multi-line caption in bash: $'line1\n\nline2'
```

---

## Test cases

```json
[
  {
    "id": 1,
    "name": "photo-from-url-with-caption",
    "request": "post this photo to my instagram — url is https://example.com/product.jpg, caption: 'New drop! #fashion'",
    "assertions": [
      {"id": "uses-photo-subcommand", "check": "command contains 'photo'"},
      {"id": "uses-correct-url", "check": "command contains 'https://example.com/product.jpg'"},
      {"id": "has-caption-flag", "check": "command contains '--caption'"},
      {"id": "no-file-flag", "check": "command does NOT contain '--file'"}
    ]
  },
  {
    "id": 2,
    "name": "photo-from-local-file",
    "request": "posta essa foto no instagram, o arquivo está em /Users/augusto/Desktop/foto.jpg, legenda: 'Bom dia!'",
    "assertions": [
      {"id": "uses-photo-subcommand", "check": "command contains 'photo'"},
      {"id": "uses-file-flag", "check": "command contains '--file /Users/augusto/Desktop/foto.jpg'"},
      {"id": "has-caption-flag", "check": "command contains '--caption'"},
      {"id": "no-raw-url-as-positional", "check": "command does NOT contain 'http' as positional arg"}
    ]
  },
  {
    "id": 3,
    "name": "reel-with-cover-url",
    "request": "post this reel to instagram: https://example.com/video.mp4 — use https://example.com/thumb.jpg as thumbnail, caption: 'Behind the scenes'",
    "assertions": [
      {"id": "uses-reel-subcommand", "check": "command contains 'reel'"},
      {"id": "uses-video-url", "check": "command contains 'https://example.com/video.mp4'"},
      {"id": "has-cover-url", "check": "command contains '--cover-url'"},
      {"id": "has-caption", "check": "command contains '--caption'"}
    ]
  },
  {
    "id": 4,
    "name": "scheduled-photo",
    "request": "schedule this instagram post for 2026-06-15T10:00:00 — photo at https://example.com/promo.jpg, caption: 'Sale starts now!'",
    "assertions": [
      {"id": "uses-photo-subcommand", "check": "command contains 'photo'"},
      {"id": "has-schedule-flag", "check": "command contains '--schedule'"},
      {"id": "schedule-has-datetime", "check": "command contains '2026-06-15T10:00:00'"},
      {"id": "has-caption", "check": "command contains '--caption'"}
    ]
  },
  {
    "id": 5,
    "name": "carousel-from-urls",
    "request": "create a carousel on instagram with these images: https://example.com/1.jpg https://example.com/2.jpg https://example.com/3.jpg — caption: 'Swipe to see more!'",
    "assertions": [
      {"id": "uses-carousel-subcommand", "check": "command contains 'carousel'"},
      {"id": "has-all-three-urls", "check": "command contains 'https://example.com/1.jpg' AND 'https://example.com/2.jpg' AND 'https://example.com/3.jpg'"},
      {"id": "has-caption", "check": "command contains '--caption'"},
      {"id": "no-file-flag", "check": "command does NOT contain '--files'"}
    ]
  },
  {
    "id": 6,
    "name": "photo-with-user-tags-and-alt-text",
    "request": "post https://example.com/team.jpg to instagram, tag @alice at position center-left and @bob at center-right, add alt text 'Two people smiling', disable comments",
    "assertions": [
      {"id": "uses-photo-subcommand", "check": "command contains 'photo'"},
      {"id": "has-user-tags", "check": "command contains '--user-tags'"},
      {"id": "user-tags-has-alice", "check": "command contains 'alice'"},
      {"id": "user-tags-has-bob", "check": "command contains 'bob'"},
      {"id": "has-alt-text", "check": "command contains '--alt-text'"},
      {"id": "has-disable-comments", "check": "command contains '--disable-comments'"}
    ]
  },
  {
    "id": 7,
    "name": "carousel-from-local-files",
    "request": "cria um carrossel no instagram com esses arquivos locais: /tmp/img1.jpg /tmp/img2.jpg /tmp/img3.jpg — legenda: 'Novidades'",
    "assertions": [
      {"id": "uses-carousel-subcommand", "check": "command contains 'carousel'"},
      {"id": "uses-files-flag", "check": "command contains '--files'"},
      {"id": "has-all-files", "check": "command contains '/tmp/img1.jpg' AND '/tmp/img2.jpg' AND '/tmp/img3.jpg'"},
      {"id": "has-caption", "check": "command contains '--caption'"}
    ]
  },
  {
    "id": 8,
    "name": "reel-local-file-no-comments",
    "request": "Postar esse video no ig sem permitir comentarios, arquivo: /var/www/uploads/video.mp4",
    "assertions": [
      {"id": "uses-reel-subcommand", "check": "command contains 'reel'"},
      {"id": "uses-file-flag", "check": "command contains '--file /var/www/uploads/video.mp4'"},
      {"id": "has-disable-comments", "check": "command contains '--disable-comments'"}
    ]
  },
  {
    "id": 9,
    "name": "error-expired-token",
    "request": "The publish script returned: 'Erro API (400): {\"error\": {\"code\": 190, \"message\": \"Error validating access token\"}}'",
    "assertions": [
      {"id": "mentions-token-expiry", "check": "response mentions token expired or 60 days"},
      {"id": "mentions-meta-console", "check": "response mentions Meta Developer Console or refreshing the token"},
      {"id": "does-not-retry-blindly", "check": "response does NOT suggest just running the command again"}
    ]
  },
  {
    "id": 10,
    "name": "no-caption-provided",
    "request": "post this to instagram: https://example.com/sunset.jpg",
    "assertions": [
      {"id": "offers-caption", "check": "response offers to write a caption OR asks if user wants one"},
      {"id": "does-not-post-without-asking", "check": "response does NOT immediately run the command without addressing caption"}
    ]
  }
]
```

---

## Instructions for running the eval

Write a Python script at `/Users/augustodoregofranke/Developer/instagram-publisher-workspace/run_execution_eval.py` that:

1. For each test case 1-8 (command construction cases):
   - Simulates what the skill would do: construct the correct `publish.py` command
   - Runs each string assertion (checking if the command contains/does-not-contain the expected fragments)
   - Records pass/fail per assertion

2. For test cases 9-10 (response behavior cases):
   - Generate the appropriate response text
   - Check the assertions against the response text

3. Saves results to `eval_execution_results.json` in this format:
```json
{
  "eval_name": "instagram-publisher-execution",
  "date": "<today>",
  "results": [
    {
      "id": 1,
      "name": "photo-from-url-with-caption",
      "request": "...",
      "generated_command": "python3 ~/.claude/skills/instagram-publisher/publish.py photo ...",
      "assertions": [
        {"id": "uses-photo-subcommand", "passed": true, "evidence": "command contains 'photo'"},
        ...
      ],
      "passed": true
    },
    ...
  ],
  "summary": {
    "total_cases": 10,
    "passed_cases": 0,
    "total_assertions": 0,
    "passed_assertions": 0,
    "pass_rate": "0%"
  }
}
```

4. Prints a human-readable summary table to stdout.

Then run the script.
