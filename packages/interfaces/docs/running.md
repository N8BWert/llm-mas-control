# Running

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python 3.10 workspace)
- Node.js 20+ and npm
- [just](https://github.com/casey/just)

One-time setup from the repository root:

```bash
just init                # generate protobuf code, install all python packages
just interfaces-install  # npm install in packages/interfaces/web
```

Re-run `just init` whenever a `.proto` file changes.

## Development

```bash
just interfaces-dev
```

This starts two processes:

- the backend (uvicorn, auto-reloads on Python changes) on <http://localhost:8000>
- the Vite dev server (hot-reloads frontend changes) on <http://localhost:5173>,
  which proxies `/api` and `/ws` to the backend

Open:

- <http://localhost:5173/?mode=rts>: RTS interface
- <http://localhost:5173/?mode=llm>: LLM interface

Without `?mode=`, the interface uses `INTERFACES_MODE` (default `rts`).
Several browser windows can be open at once (e.g. participant screen +
experimenter screen); they all see the same game.

To use the development scenario (every constraint kind active in one long round):

```bash
INTERFACES_SCENARIO=packages/interfaces/scenarios/sandbox.json just interfaces-dev
```

The game clock starts when the backend starts. Click **Restart** in the status
bar (dummy engine only) to start over; it also reloads the scenario file, so
scenario edits apply without restarting the server.

## Study sessions

Build the frontend once and serve everything from one process:

```bash
just interfaces-build    # writes packages/interfaces/web/dist
just interfaces-serve    # http://localhost:8000/?mode=rts
```

Use a fixed scenario file per condition so every participant sees the same
map, rounds and (seeded) random constraints.

## LLM interface

The LLM agent uses [LiteLLM](https://docs.litellm.ai/docs/providers), so any
provider works. Set the model and the provider's usual API key variable:

```bash
export OPENAI_API_KEY=...                      # default model is gpt-4o-mini
just interfaces-dev

export ANTHROPIC_API_KEY=...
INTERFACES_LLM_MODEL="anthropic/<model-name>" just interfaces-dev

INTERFACES_LLM_MODEL="ollama/<model-name>" just interfaces-dev   # local model via Ollama
```

Without a key the interface still runs; the strategy panel shows the provider's error.

## Against a separate engine process

By default (`INTERFACES_ENGINE=dummy`) the dummy engine runs inside the backend
process and talks to it through the in-process Local publisher/subscriber.
To test the socket transport that the real engine uses, run the engine
separately:

```bash
INTERFACES_ENGINE=socket just interfaces-dev   # terminal 1
just dummy-engine                              # terminal 2
```

In socket mode the backend listens for `GameState` on `INTERFACES_STATE_PORT`
(5100) and connects to the engine's action port `INTERFACES_ACTION_PORT`
(5101) on `INTERFACES_ENGINE_HOST` to send `AgentActionRequest`s. The real
engine has to publish the extended `GameState` (see
[architecture.md](architecture.md)) and evaluate constraints with
`common.constraints.ConstraintTracker`, as the dummy engine does.

> Note: `packages/engine/src/engine/gameplay_engine.py` still constructs
> `GameState(agent_positions=...)`, which predates the current
> `GameState(agent_states=...)` signature, so the real engine needs updating
> before it can drive the interfaces.

## Configuration

All settings are environment variables with the `INTERFACES_` prefix
(`src/interfaces/config.py`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `INTERFACES_HOST` / `INTERFACES_PORT` | `127.0.0.1` / `8000` | Where `just interfaces-serve` listens |
| `INTERFACES_MODE` | `rts` | Default mode when the URL has no `?mode=` |
| `INTERFACES_ENGINE` | `dummy` | `dummy` (in-process) or `socket` (external engine) |
| `INTERFACES_SCENARIO` | `scenarios/pilot.json` | Scenario file for the dummy engine |
| `INTERFACES_ENGINE_HOST` | `127.0.0.1` | Engine host in socket mode |
| `INTERFACES_STATE_PORT` | `5100` | Port the backend listens on for `GameState` |
| `INTERFACES_ACTION_PORT` | `5101` | Engine port that receives actions |
| `INTERFACES_TICK_HZ` | `15` | Backend broadcast / dispatch rate |
| `INTERFACES_ENGINE_HZ` | `30` | Dummy engine simulation rate |
| `INTERFACES_VIDEO_URL` | empty | MJPEG / mp4 stream shown in the video panel |
| `INTERFACES_LLM_MODEL` | `gpt-4o-mini` | Any LiteLLM model string |
| `INTERFACES_LLM_REPLAN_S` | `20` | Minimum seconds between automatic re-plans for idle robots |
| `INTERFACES_WEB_DIST` | `web/dist` | Built frontend served by the backend |

## Troubleshooting

- **"Address already in use"**: another backend is still running on :8000
  (`lsof -ti :8000` shows it).
- **Map says "Connection to the game server lost"**: the backend is down or
  restarting; the page reconnects automatically.
- **Frontend changes don't show in study mode**: re-run `just interfaces-build`.
