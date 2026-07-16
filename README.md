# Nimbus Chat — Django Channels real-time chat

A Slack-style workspace chat app: Django + Django Channels (WebSockets) +
Redis for the channel layer + PostgreSQL for storage, with a small DRF
API for message history. Session auth, workspaces with invite codes,
public/private channels, live messaging, typing indicators, and emoji
reactions all work end to end.

## Project layout

```
chatapp/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── chatapp/            Django project (settings, urls, asgi)
└── core/                the app: models, views, consumers, templates
```

---

## 1. Run it locally WITHOUT Docker (fastest way to try it)

Requirements: Python 3.11+ installed.

```bash
# 1. Unzip and enter the project
cd chatapp

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy env file (defaults use sqlite + in-memory channel layer, no Redis/Postgres needed)
cp .env.example .env

# 5. On Linux/macOS, load the .env into your shell (or use python-dotenv / direnv)
export $(grep -v '^#' .env | xargs)

# 6. Create the database tables
python manage.py migrate

# 7. Create an admin user (optional, for /admin/)
python manage.py createsuperuser

# 8. Run the ASGI server (runserver does NOT support websockets — use daphne)
daphne -b 0.0.0.0 -p 8000 chatapp.asgi:application
```

Open **http://127.0.0.1:8000** — sign up, create a workspace, create a
channel, and start chatting. Open the same channel in two browser
windows (or two browsers) logged in as two different users to see
real-time messages, typing indicators, and reactions sync live.

> Note: with no `REDIS_URL` set, the channel layer runs in-memory —
> that's fine for one `daphne` process, but messages won't sync across
> multiple worker processes. Add Redis (see below) once you need that.

### Adding Redis locally (recommended once you go beyond one process)

```bash
# macOS
brew install redis && brew services start redis
# Ubuntu/Debian
sudo apt install redis-server && sudo systemctl start redis-server
```

Then set in `.env`:
```
REDIS_URL=redis://127.0.0.1:6379
```
Reload the env vars and restart daphne.

---

## 2. Run it locally WITH Docker (matches production setup)

Requirements: Docker + Docker Compose installed.

```bash
cd chatapp
cp .env.example .env
docker compose up --build
```

This starts three containers: `db` (Postgres), `redis`, and `web`
(migrates automatically, then serves via daphne on port 8000).

Open **http://127.0.0.1:8000**.

Run one-off management commands inside the running container:
```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py migrate
```

Stop everything:
```bash
docker compose down          # add -v to also wipe the Postgres volume
```

---

## 3. Deploying it live

The container already does the right thing (`migrate` then `daphne`),
so any host that runs a Dockerfile works. Two common paths:

### Option A — a VPS you control (DigitalOcean, Hetzner, EC2, etc.)

```bash
# on the server
git clone <your-repo-url> chatapp && cd chatapp
cp .env.example .env
# edit .env: set a real SECRET_KEY, DEBUG=False, ALLOWED_HOSTS=yourdomain.com,
# CSRF_TRUSTED_ORIGINS=https://yourdomain.com
docker compose up --build -d
```
Put nginx (or Caddy) in front as a reverse proxy to terminate TLS and
forward both HTTP and WebSocket upgrade requests to `web:8000`. An
nginx location block needs the standard websocket upgrade headers:
```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```
Use `certbot` (Let's Encrypt) for a free TLS certificate.

### Option B — a platform-as-a-service (Render, Railway, Fly.io)

These all build your `Dockerfile` directly, so the steps are the same
shape on each:
1. Push this project to a GitHub repo.
2. Create a new "web service" from that repo and let it build the Dockerfile.
3. Add a managed Postgres add-on and a managed Redis add-on from the
   same platform, and copy their connection details into your service's
   environment variables (`POSTGRES_*`, `REDIS_URL`).
4. Set `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<your-app>.onrender.com`
   (or your custom domain), and `CSRF_TRUSTED_ORIGINS=https://<your-app>...`.
5. Make sure the platform exposes the WebSocket protocol on the same
   port as HTTP — all three of these platforms do this by default for
   a single web service; confirm in their current dashboard docs since
   exact steps/UI change over time.

Whichever platform you pick, double check its current docs for exact
steps — dashboards change — but the underlying Dockerfile and
environment variables above don't need to change.

---

## 4. Environment variables reference

| Variable | Purpose | Local default |
|---|---|---|
| `SECRET_KEY` | Django cryptographic signing key | insecure dev key (change for production) |
| `DEBUG` | Django debug mode | `True` |
| `ALLOWED_HOSTS` | comma-separated allowed hostnames | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | comma-separated origins allowed to POST | empty |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Postgres connection; unset → sqlite | unset |
| `REDIS_URL` | Channels layer backend; unset → in-memory | unset |

---

## 5. What's implemented vs. what's next

**Working now:** signup/login/logout, create/join workspace by invite
code, public and private channels, real-time messaging over
WebSockets, typing indicators, emoji reactions, message history
persisted in the database, role field (admin/member) on membership,
a read-only DRF API endpoint for message history
(`/api/w/<workspace>/c/<channel>/messages/`).

**Natural next additions:** direct messages (the `Channel.is_dm` field
and `ChannelMembership` model already support it — add a "start DM"
view that creates a 2-person private channel), file uploads
(add a `FileField` to `Message` and handle multipart POST alongside
the websocket text messages), full-text message search (Postgres
`SearchVector` on `Message.content`), and per-workspace admin
permission checks on channel creation/deletion.
"# nexusflow" 
