# Developing

Run `just interfaces-dev` with the sandbox scenario while developing (see
[running.md](running.md)). Python changes reload the backend; frontend
changes hot-reload in the browser.

## Incorporating LLMs

The LLM interface lives in `src/interfaces/llm/` and has three parts.

### When the LLM plans (`agent.py`)

`LlmAgent` is called every tick with the latest view (`observe`). It requests
a plan when:

- the operator sends a new strategy (`set_strategy`),
- a new constraint becomes active, or
- some robots are idle with empty queues and `INTERFACES_LLM_REPLAN_S` seconds
  have passed since the last plan.

Only one plan runs at a time. An emergency stop/retreat calls `halt()`, which
pauses planning until the operator sends a new strategy. Every step is
written to the agent's `log` (shown in the strategy panel): operator input,
the model's text, applied commands, rejected tool calls, and system notes.

A plan is a single LiteLLM `acompletion` call with tools. Each returned tool
call is applied to the command queue with `source="llm"`.

### What the LLM sees (`prompt.py`)

- `SYSTEM_PROMPT`: role, game rules and how to use the tools. Update this when
  game mechanics change.
- `describe_state(view)`: converts the same JSON view the browser gets into
  compact text: score/round/time, arena and tile math, map features by tile,
  each robot (role, position, health, action, cargo, queued commands),
  enemies, objectives, and every active constraint with its state, offenders
  and timers.
- `build_messages(strategy, view, reason)`: system + one user message with
  the strategy, why it is being asked now, and the state.

To give the LLM more information (e.g. a summary of recent violations), add it
to `describe_state`. Because it works from the view, anything the UI can show
is available.

### What the LLM can do (`tools.py`)

`TOOLS` holds OpenAI-style function schemas; `apply_tool_call` turns a call into
queue operations and returns a summary for the log (or raises `ValueError`,
which is logged as rejected). Current tools:

- `queue_command(robot_ids, action, x, y, append)`: same as an RTS command
- `clear_commands(robot_ids)`

To add a tool, add its schema to `TOOLS` and a branch in `apply_tool_call`.
For example, a tool that sends robots to an objective:

```python
# in TOOLS
{"type": "function", "function": {
    "name": "hold_position",
    "description": "Send robots to a point and keep them there.",
    "parameters": {"type": "object", "properties": {
        "robot_ids": {"type": "array", "items": {"type": "integer"}},
        "x": {"type": "number"}, "y": {"type": "number"}},
        "required": ["robot_ids", "x", "y"]}}}

# in apply_tool_call
if name == "hold_position":
    queue.add(ids, "move", (float(args["x"]), float(args["y"])), source="llm")
    return f"robots {ids} holding at ({args['x']}, {args['y']})"
```

### Swapping models or the planning approach

- **Provider/model**: set `INTERFACES_LLM_MODEL` to any LiteLLM model string.
- **Custom calls** (structured output, multi-step reasoning, another SDK):
  `LlmAgent` takes a `completion` coroutine that receives the same keyword
  arguments as `litellm.acompletion` and returns an object with
  `choices[0].message.content` and `.tool_calls`. `tests/test_llm.py` shows a
  fake one, which is also the pattern for offline tests.
- **Different triggers** (e.g. re-plan on every violation): change `observe()`.

## Adjusting game rules and mechanics

Where each rule lives:

| Rule | Where |
| --- | --- |
| Map, robot count, roles, speed, action durations, points, rounds, constraints | Scenario JSON (`scenarios/*.json`) — no code |
| What each action does (which tile, which item, what it builds) | `TILE_RULES` in `sim/dummy_engine.py` (and the real engine) |
| Enemy damage | `ENEMY_DAMAGE_PER_S` in `sim/dummy_engine.py` |
| Constraint kinds and their evaluation | `common/constraints/definitions.py` |
| Penalty accounting | `common/constraints/tracker.py` |
| When the next queued command starts | `CommandQueue.dispatch` in `commands.py` |
| Emergency stop / retreat behavior | `CommandQueue.emergency` in `commands.py` |
| Rules the LLM is told | `SYSTEM_PROMPT` in `llm/prompt.py` |

### Scenario files

A scenario is a complete, reproducible game session. Fields (see
`common/scenario.py`):

```jsonc
{
  "name": "pilot",
  "seed": 7,                                // seeds the random constraint draws
  "n_robots": 6,
  "robot_speed": 0.15,                      // m/s in the dummy engine
  "roles": ["worker", "worker", "builder", "scout"],   // robot i gets roles[i % len]
  "arena": [-1.6, -1.0, 1.6, 1.0],          // x_min, y_min, x_max, y_max (m)
  "grid": [32, 20],                         // tiles along x, y
  "home": [-1.25, 0.05],                    // robots spawn in a ring around this point
  "tiles": [
    {"state": "CASTLE", "x": 3, "y": 10},
    {"state": "QUARRY", "x": 26, "y": 15, "w": 2, "h": 2}   // w/h fill a block
  ],
  "enemies": [{"id": 1, "label": "Patrol", "path": [[0.45, -0.75], [0.45, 0.75]],
               "speed": 0.05, "radius": 0.2}],              // patrols back and forth
  "objectives": [{"id": 1, "label": "Supply drop", "position": [0.9, -0.6]}],
  "action_durations": {"mine": 5, "farm": 4},               // seconds of work on arrival
  "action_points": {"build_house": 15},                     // points for completing an action
  "item_points": {"stone": 10, "food": 6, "apple": 4},      // points when dropped at the castle
  "rounds": [
    {"name": "Easy", "duration_s": 120,
     "constraints": [ /* always active this round */ ],
     "random_pool": [ /* candidates */ ], "pick": 1}         // draw `pick` from the pool
  ]
}
```

Tile states are the names in `common/tile.py` (`EMPTY`, `CASTLE`, `FARM`,
`QUARRY`, `WATER`, `APPLE`, `OBSCURED`). Random constraints are drawn with
`random.Random(f"{seed}-{round_index}")`, so the same file always yields the
same constraints.

### Constraints in scenarios

Every constraint has `kind`, `id`, and optionally `label`, `description`
(auto-generated if omitted), `difficulty`, `penalty` (points per violation,
default 10), `active_from_s` and `active_until_s` (seconds into the round).
Zones are `{"rect": [x_min, y_min, x_max, y_max]}` or `{"circle": [x, y, r]}`.

| Kind | Fields | Violated when | Warning when |
| --- | --- | --- | --- |
| `restricted_zone` | `zones` | a robot is inside | a robot is heading into one |
| `occupation_zone` | `zones`, `min_robots`, `grace_s` | a zone has too few robots after the grace period | during the grace period |
| `timed_entry_zone` | `zones`, `max_dwell_s` | a robot stays inside longer than the limit | at 75% of the limit |
| `activity_interval` | `max_active_s`, `base_zone` | a robot has been away from base longer than the limit | at 75% of the limit |
| `role_restriction` | `action_kinds`, `allowed_roles` | a robot of another role performs the action | such a robot is assigned the action |

Penalties are **edge-triggered**: a violation costs points once when it
starts (per robot, or per zone for occupation), not every tick it lasts.
Leaving and re-entering counts again.

Example: a no-go zone that appears 30 s into the round for 60 s:

```json
{"kind": "restricted_zone", "id": "flood", "label": "Flooded area",
 "difficulty": "medium", "penalty": 15, "active_from_s": 30, "active_until_s": 90,
 "zones": [{"rect": [-0.2, -0.4, 0.3, 0.1]}]}
```

### Adding a new constraint kind

1. **Proto**: add a message and a new field in `Constraint.kind` in
   `protos/common/protos/constraint.proto`; run `just init`.
2. **Evaluation**: in `common/constraints/definitions.py`, subclass
   `Constraint` with `KIND` set to the oneof field name, implement
   `describe()`, `evaluate()`, `_kind_proto()` and `_kind_kwargs()`, and add
   the class to `CONSTRAINT_KINDS`. `evaluate(t, dt, agents, memory)` returns
   an `Evaluation(state, offending_robot_ids, timers, zone_counts,
   violation_keys)`; `memory` is a dict that persists between ticks while
   the constraint is active (use it for timers). Each distinct key in
   `violation_keys` is penalized once when it first appears.
3. **Export** it from `common/constraints/__init__.py` and add tests in
   `packages/common/tests/test_constraints.py`.
4. **UI**: add the field to `Constraint` in `web/src/types.ts` and to `KINDS`
   / `constraintZones()` there. Pick a style in `zoneStyle()` in
   `map/constraintLayer.ts` and, if it uses timers, a ring in
   `robotConstraintRings()`. Kind-specific detail lines go in
   `details()` in `panels/ConstraintPanel.tsx`.

The LLM picks the constraint up automatically through its `description`.

### Adding a new action

1. Add the action class in `common/actions/` (and its proto) if it doesn't
   exist.
2. Map a kind string to it in `TILE_ACTIONS` in `src/interfaces/actions.py`
   (this also adds it to the LLM tool enum and `/api/config`).
3. Give it a rule in `TILE_RULES` in `sim/dummy_engine.py` and a duration
   and/or points in the scenario.
4. In the frontend, add it to `ACTION_TOOLS` in `panels/CommandBar.tsx`
   (button + number hotkey) and, if it should be a right-click default for a
   tile type, to `SMART_ACTIONS` in `map/tools.ts`.
5. Mention it in `SYSTEM_PROMPT`.

### The real engine

The interfaces only need the engine to:

- receive `AgentActionRequest` (one action per robot, replacing its current one),
- report each robot's `busy` flag (the queue starts the next command when it
  turns false) and, ideally, the extended `AgentState` fields,
- publish `GameState` including `active_constraints` and
  `constraint_statuses` from a `ConstraintTracker`.

`sim/dummy_engine.py` is a compact reference for all three.

## Frontend development

- **State** is a set of signals in `state/store.ts`; components read them
  directly and re-render automatically. Only `api/socket.ts` writes
  server-driven signals.
- **Sending** anything to the backend goes through `api` in `api/socket.ts`.
- **Map drawing** is in `map/MapView.ts` (one Konva layer per concern; the
  terrain is cached and only redrawn when tiles change). Map **interaction**
  is in `map/tools.ts`, which keeps MapView free of game logic.
- **Panels** are independent components in `panels/`; add a panel by writing
  a component and placing it in `App.tsx` (use `mode.value` to show it only
  in one interface).
- **Colors** live in `theme.ts`.
- **Notifications**: call `notify(text, kind)` from `state/store.ts` to show a
  toast.

Type-check and test with `npm run typecheck` and `npm test` in `web/`.

## Tests

| Suite | Command | Covers |
| --- | --- | --- |
| common | `just test common` | Zones, every constraint kind, tracker penalties, proto/dict round trips, scenarios |
| interfaces | `just test interfaces` | Command queue, dummy engine rules and rounds, view model, server WebSocket protocol, LLM tools/prompt/agent (fake model) |
| web | `cd web && npm test` | World/screen transform, tile math, path-vs-zone tests, selection |
