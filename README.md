# discord-webhook-starter

**The simplest correct Discord slash-command bot: one FastAPI file, signed interactions, no gateway loop, no `while True`.**

[![ci](https://github.com/mgkvibez/discord-webhook-starter/actions/workflows/ci.yml/badge.svg)](https://github.com/mgkvibez/discord-webhook-starter/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![no gateway](https://img.shields.io/badge/connection-http%20only-brightgreen.svg)](#why-not-a-gateway)

Most Discord tutorials start with `client.run("TOKEN")`, a persistent WebSocket that must stay connected forever. This does the opposite: Discord sends an HTTP POST to your server when someone runs a slash command, and your server answers. It sleeps between requests, runs on a free instance, and dies cleanly when idle.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mgkvibez/discord-webhook-starter)

---

## First: three different things are called a Discord webhook

This is the confusion that costs people an afternoon, so it gets the top of the README.

| What you want | Discord calls it | Where it lives | This repo |
|---|---|---|---|
| Respond to `/slash` commands, buttons, autocomplete | **Interactions Endpoint URL** | Developer Portal → General Information | `POST /interactions` |
| Post messages into a channel from your app, no bot user | **Incoming webhook** | Channel → Integrations → Webhooks | `POST /admin/notify` |
| React to every message people type, presence, joins | **Gateway** (WebSocket) | `discord.py`'s `client.run()` | Not here, and that is deliberate |

If you want "my CI pipeline posts a message when a deploy finishes", you want an incoming webhook and `/admin/notify`. If you want "people run `/hello` in my server", you want the interactions endpoint and `/interactions`. If you need to read ordinary chat messages, you need the gateway, and no HTTP endpoint will do it.

## Why not a gateway

A gateway bot holds one WebSocket connection open per shard, forever. That means a process that never sleeps, which most free hosting does not give you. The HTTP endpoint model has no connection at all: Discord calls you, you answer, you go back to sleep. For a bot that responds to commands, that is strictly less to run and less to break.

The trade-off, stated plainly: **no HTTP endpoint can read ordinary messages**. Discord only sends message *content* over the gateway. If your bot needs to read chat, use a gateway client.

## 60-second setup

1. **Create the application.** [Developer Portal](https://discord.com/developers/applications) → New Application. On **General Information**, copy the **Application ID** and **Public Key**. Both go in your environment.
2. **Deploy this repo.** Use the Render button above, or `docker build` and run it anywhere that gives you HTTPS. Copy the **Public Key** and **Application ID** into the environment variables.
3. **Set the endpoint URL.** Back on General Information, paste `https://<your-host>/interactions` into **Interactions Endpoint URL** and save.
   Discord immediately sends a `PING`, and the URL only saves if your server answers `PONG` with a valid Ed25519 signature. That handshake is why `app.py` checks the signature *and* answers type 1 before anything else. If it refuses to save, you have a signature problem, not a URL problem.
4. **Register the commands.** The bot token is only needed for this one call:
   ```bash
   curl -X POST https://<your-host>/admin/register-commands \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
   Set `DISCORD_GUILD_ID` first if you want the commands to appear instantly instead of within the hour.
5. **Invite the bot**, type `/hello`, and watch it answer.

## What you get

```
/hello   → greeting with a link button
/ping    → liveness check
/slow    → deferred acknowledgement, then a follow-up notice
```

Clicking a button sends a component interaction (type 3) and the handler answers it the same way it answers a command. Unknown commands and unknown buttons reply privately (`flags: 64`) so you never spam a channel while building.

## The three-second rule

Discord kills an interaction if your server has not answered within three seconds. The user then sees **"This interaction failed"** and no amount of later work brings it back. Two options:

- Answer immediately (what `/hello` and `/ping` do).
- Acknowledge with a deferred response (type 5), do the slow work, then POST a follow-up message with the interaction token. That is exactly what `/slow` demonstrates, and the token is valid for 15 minutes.

`/slow` returns type 5 in milliseconds and schedules the follow-up as a background task, so a slow database or API call never blocks the acknowledgement.

## Add your own command

Three edits, no framework knowledge needed:

```python
# 1. bot/commands.py: tell Discord the command exists
{"name": "weather", "description": "Show the weather in a city", "type": 1},

# 2. bot/handlers.py: answer it
if name == "weather":
    return Reply(R.message("It is probably fine."))

# 3. re-register
curl -X POST https://<your-host>/admin/register-commands -H "Authorization: Bearer $ADMIN_TOKEN"
```

Command arguments arrive in `payload["data"]["options"]`, which `handlers.py` deliberately does not parse yet, so you can add them without fighting existing code.

## Security, since this is a public endpoint

**Signature verification is mandatory, not optional.** Discord signs every request with Ed25519 over `timestamp + body` and shows you the public key. Without checking it, anyone who learns your URL can POST fake commands. `bot/verify.py` does the check with PyNaCl, the same library Discord's Python examples use.

Two details that break naive implementations:

- **Verify the raw bytes.** The signature covers the exact body Discord sent, so `await request.body()` happens *before* `json.loads`. Parse first and you are verifying nothing.
- **A stale timestamp is a replay.** Signatures are rejected once they are older than `DISCORD_TIMESTAMP_TOLERANCE` seconds (default 300). Set it to `0` only if you have a clock you distrust.

Admin routes (`/admin/*`) require a bearer token from `ADMIN_TOKEN` and refuse to run at all when that variable is unset. Nothing logs a token, and errors surface as status codes with short detail rather than echoing request bodies.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app:app --reload
```

Telegram, Discord, and Discord's endpoint box all need a public HTTPS address, so for local work point the endpoint URL at whatever public HTTPS address reaches your machine (a platform preview URL works fine), or deploy the free instance and develop against that. The app itself does not care where it runs.

Check it is alive without Discord at all:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/interactions -d '{"type":1}'   # 401, as it should be
```

## Tests

**47 tests, offline, no Discord account, no network.** Real Ed25519 keys are generated per test, so signature verification is genuinely exercised rather than mocked out; the HTTP client is tested against `httpx.MockTransport`.

```bash
pytest -q      # 47 passed
bash scripts/verify.sh
```

The gate runs ruff, the suite, an import check with an empty environment, then boots the real server and asserts the three things that matter over real HTTP: `/health` is 200, an unsigned interaction is 401, and the admin route is 401/503. It also greps for `discord.py` and `client.run` and fails if a gateway client ever creeps in.

## Troubleshooting

| Symptom | Cause |
|---|---|
| **Interactions Endpoint URL** will not save | Signature check failing or PING not answered with `{"type": 1}`. Check that `DISCORD_PUBLIC_KEY` is the hex key from General Information, not the application ID. |
| "This interaction failed" | No response within three seconds. Defer with type 5 and follow up. |
| Slash commands do not appear | Not registered yet, or registered globally (can take an hour). Set `DISCORD_GUILD_ID` and re-register for instant availability. |
| Every request returns 401 | Public key mismatch, clock skew beyond the tolerance, or the body was parsed before it was verified. |
| "Bot is not responding" after a deploy | Free instances sleep. Discord still shows commands, but a sleeping instance cannot answer in three seconds; the first request after sleep can miss the deadline. |

## Limits, honestly

No message content without a gateway. No persistence: this starter keeps nothing, which is why duplicate-delivery handling is not implemented. No command options parsing yet (documented above). No sharding, no shard count, no rate-limit queue beyond what the follow-up path needs. If your bot grows into reading messages, this repo is the wrong tool and a gateway client is the right one.

## License

MIT. Do whatever you like with it.
