# hermes-grok-usage

SkyMin [Hermes Agent](https://github.com/NousResearch/hermes-agent) desktop plugin. Shows SuperGrok weekly (or monthly) usage on the Hermes desktop status bar.

GitHub repo name: `hermes-grok-usage`. Plugin id stays `grok-usage`.

Speech/output plugins (caveman, i-have-adhd, ponytail, rtk-rewrite) live in [hermes-plugins](https://github.com/SYacuCLoud/hermes-plugins).

## What you get

- Status-bar chip: `Grok 42%` (or `Grok —` if usage is unknown).
- Tooltip: period, percent, reset time.
- Turns hot at 80% used.
- Backend: Hermes xAI OAuth token against Grok CLI billing (`cli-chat-proxy.grok.com`). Not a public xAI API.
- Desktop chip polls every 120s. Python backend caches 90s.

## Layout

```
plugin.yaml              # Hermes plugin manifest
dashboard/
  plugin_api.py          # GET /usage for the chip
  manifest.json
desktop/
  plugin.js              # status-bar chip (Hermes desktop plugin SDK)
```

## Install

Two halves. Both needed.

**Python backend** (gateway / `plugins.enabled`):

1. Copy this folder to `$HERMES_HOME/plugins/grok-usage/`.
2. Enable:

```bash
hermes plugins enable grok-usage
```

3. Restart Hermes.

**Desktop chip**:

- Either leave `desktop/plugin.js` inside `plugins/grok-usage/desktop/` (unified package; enable it in Settings → Plugins — this half is opt-in).
- Or copy `desktop/plugin.js` to `$HERMES_HOME/desktop-plugins/grok-usage/plugin.js` (standalone desktop plugin; loads by default).

Sign in to xAI in Hermes first. Chip shows “xAI login missing” when there is no token.

## Requirements

- Hermes desktop app (CLI/gateway alone does not render the chip).
- xAI OAuth already configured in Hermes.
- SuperGrok / Grok CLI billing account the token can read.

## License

Personal / public source dump. Author: SkyMin (`syacucloud`).
