import json
import re
from jsonschema import Draft202012Validator



# Level 1: JSON formatting
def parse_json_strict(text: str):
    """
    Parses the string as a JSON object.
    """
    assert isinstance(text, str)

    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

def parse_json_lenient(text: str):
    """
    Parses the string as a JSON object,
    but also forgives any leading mess (in case the LLM bloviates).
    """
    assert isinstance(text, str)

    dec = json.JSONDecoder()
    starts = sorted({m.start() for m in re.finditer(r"^\{", text, re.M)})
    for pos in starts:
        if pos < 0:
            continue
        try:
            obj, _ = dec.raw_decode(text[pos:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None

# Level 2: Schema matching
def schema_errors(instance, schema):
    v = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in sorted(v.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))]

# Level 3: Game semantics
GRID_COLUMNS = "ABCDEFGHIJKLMNOP"
GRID_ROWS = 16
_CELL_RE = re.compile(r"^([A-Z])([0-9]+)$")

def is_cell(symbol):
    return _CELL_RE.match(symbol) is not None

def cell_in_bounds(cell):
    m = _CELL_RE.match(cell)
    return bool(m) and m.group(1) in GRID_COLUMNS and 1 <= int(m.group(2)) <= GRID_ROWS

ALLOWED_TARGETS = {
    "move": {"cell", "castle", "house", "farm", "quarry", "apple"},
    "pick_up": {"apple"},
    "drop": {"castle", "cell"},
    "build_farm": {"cell", "castle", "house", "farm", "quarry"},
    "build_house": {"cell", "castle", "house", "farm", "quarry"},
    "build_quarry": {"cell", "castle", "house", "farm", "quarry"},
    "farm": {"farm"},
    "mine": {"quarry"},
}
WORK_AFTER_BUILD = {"build_farm": "farm", "build_quarry": "mine"}

def reference_errors(state, out):
    errs = []
    ants = {a["id"]: a for a in state["ants"]}
    entities = {e["id"]: e for e in state["entities"]}
 
    # status consistency
    if out["status"] == "ok":
        if out["refusal_reason"] is not None:
            errs.append("status ok but refusal_reason is set")
        if not (out["cancels"] or out["orders"]):
            errs.append("status ok but cancels and orders are both empty")
    else:
        if out["refusal_reason"] is None:
            errs.append("status refused but refusal_reason is null")
        for k in ("cancels", "orders", "unhandled"):
            if out[k]:
                errs.append(f"status refused but {k} is not empty")
 
    def check_subjects(subjects, where):
        for s in subjects:
            if s not in ants:
                errs.append(f"{where}: unknown subject {s}")
 
    # cancels
    for i, c in enumerate(out["cancels"]):
        where = f"cancels[{i}]"
        check_subjects(c["subjects"], where)
        if c["scope"] == "ids":
            if not c["command_ids"]:
                errs.append(f"{where}: scope ids needs command_ids")
            known = {q["cmd_id"] for a in c["subjects"] if a in ants for q in ants[a]["queue"]}
            for cid in c["command_ids"]:
                if cid not in known:
                    errs.append(f"{where}: command id {cid} not in the subjects' queues")
        elif c["command_ids"]:
            errs.append(f"{where}: command_ids must be [] unless scope is ids")
 
    # orders
    for i, o in enumerate(out["orders"]):
        where = f"orders[{i}]"
        check_subjects(o["subjects"], where)
        prev_action = None
        for j, s in enumerate(o["steps"]):
            sw = f"{where}.steps[{j}]"
            action, target = s["action"], s["target"]
            if target == "just_built":
                if WORK_AFTER_BUILD.get(prev_action) != action:
                    errs.append(f"{sw}: just_built must directly follow a matching build step")
            else:
                cls = None
                if target in entities:
                    cls = entities[target]["kind"]
                elif is_cell(target):
                    if cell_in_bounds(target):
                        cls = "cell"
                    else:
                        errs.append(f"{sw}: cell {target} is outside the grid (A1 to {GRID_COLUMNS[-1]}{GRID_ROWS})")
                else:
                    errs.append(f"{sw}: unknown target {target}")
                if cls is not None and cls not in ALLOWED_TARGETS[action]:
                    errs.append(f"{sw}: {action} cannot target a {cls} ({target})")
            prev_action = action
    return errs
