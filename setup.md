# Setup Guide — Instagram Publisher

This guide prepares everything the skill needs to publish to Instagram. Do this once.

---

## Step 1 — Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com) and log in with your Facebook account.
2. Click **My Apps → Create App**.
3. Select **Other** as the use case, then **Business** as the app type.
4. Give it a name (e.g. "Claude Instagram Publisher") and click **Create App**.

---

## Step 2 — Connect your Instagram Business account

Your Instagram account must be a **Professional account** (Business or Creator) connected to a Facebook Page.

1. Inside your app dashboard, go to **Add Products** and add **Instagram Graph API**.
2. Under **Instagram Graph API → Basic Display**, add your Instagram account as a test user.
3. In **App Roles → Roles**, add your Instagram account.

> If your account is Personal, go to Instagram Settings → Account → Switch to Professional Account first.

---

## Step 3 — Get your credentials

### IG_USER_ID

1. In the Meta Developer Console, go to **Instagram Graph API → Getting Started**.
2. Use the Graph API Explorer (`graph.facebook.com/me/accounts`) to find your Instagram Business Account ID.
3. Or call: `https://graph.instagram.com/me?fields=id,username&access_token=<your_token>`

### ACCESS_TOKEN (long-lived)

1. In the Graph API Explorer, generate a short-lived token with these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
2. Exchange it for a long-lived token (valid 60 days) by calling:
   ```
   https://graph.instagram.com/access_token
     ?grant_type=ig_exchange_token
     &client_id=<app_id>
     &client_secret=<app_secret>
     &access_token=<short_lived_token>
   ```
3. Save the returned `access_token`.

> **Token expiry:** long-lived tokens last 60 days. Refresh before expiry by calling the same endpoint with your current long-lived token. Set a calendar reminder.

---

## Step 4 — Create the .env file

Create the file at `~/.claude/skills/instagram-publisher/.env`:

```
IG_USER_ID=<your numeric Instagram Business user ID>
ACCESS_TOKEN=<your long-lived access token>
```

No quotes around the values. Example:

```
IG_USER_ID=17841400000000000
ACCESS_TOKEN=EAABsB...longstring...
```

---

## Step 5 — Set up Tailscale Funnel (for local files only)

Skip this step if you only post from URLs.

Tailscale Funnel lets the skill serve a local file over a public HTTPS URL so Instagram can fetch it.

1. Install Tailscale: [tailscale.com/download](https://tailscale.com/download)
2. Log in: `tailscale up`
3. Enable Funnel on your account: go to [login.tailscale.com/admin/dns](https://login.tailscale.com/admin/dns) → enable **HTTPS Certificates**, then [login.tailscale.com/admin/acls](https://login.tailscale.com/admin/acls) → add Funnel to your ACL policy:
   ```json
   "nodeAttrs": [
     {
       "target": ["<your-machine-tag-or-email>"],
       "attr": ["funnel"]
     }
   ]
   ```
4. Verify: `tailscale funnel status` — should show no errors.

---

## Step 6 — Verify everything works

Run a quick test with a public image URL (no local file needed):

```bash
python3 ~/.claude/skills/instagram-publisher/publish.py photo \
  "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png" \
  --caption "Test post from Claude 🤖"
```

If you see a permalink printed at the end, you're all set.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `IG_USER_ID not set` | Check that `.env` exists at the right path and has no typos |
| `Error 190` or `invalid token` | Token expired — repeat Step 3 to get a new one |
| `Error 10` / permissions | Make sure `instagram_content_publish` permission is granted in the app |
| `Funnel not reachable` | Check `tailscale status` and confirm Funnel is enabled in ACL |
| `Error 352` / unsupported format | Re-encode video: `ffmpeg -i input.mov -vcodec libx264 -acodec aac output.mp4` |
