# AS LIKE BOT — Web Store

Mobile-first web version of the AS LIKE BOT system. It uses the uploaded bot's main Like API and Info API, and the supplied user.html as the visual starting point.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/Android: source .venv/bin/activate
pip install -r requirements.txt
export BOHUDUR_API_KEY="YOUR_BOHUDUR_KEY"
python server.py
```

Open `http://127.0.0.1:5000/` and admin at `http://127.0.0.1:5000/admin`.

## Deploy

GitHub stores the repository; Python must run on a server platform such as Render/Railway/VPS. Set `BOHUDUR_API_KEY` as a server-side secret. Do **not** put the Bohudur key in `index.html` or a public GitHub file. Bohudur's docs explicitly require the API key to stay server-side.

## Current integrations

- Like API: `https://asfflikebdlikeapi.vercel.app/like` with `uid` and `server_name=BD`.
- Info API: `https://ffxinfo-ffx.ffxapis.workers.dev/ffinfo?uid=...`.
- Bohudur create → hosted checkout → query → execute flow.
- Admin page has no login, as requested. Because there is no login, do not expose this admin URL publicly until Firebase/auth is added.

## Firebase later

The API routes are intentionally separated from the UI so Firebase can be added later for users, balances, order history, and admin authorization without rewriting the store UI.
