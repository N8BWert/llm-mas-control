# Justfile for working with the llm-mas-control project

PROTO_DIR := "protos"
COMMON_PROTO_DIR := "packages/common/src"

# Initialize the project
init:
    uv run python -m grpc_tools.protoc \
        -I={{PROTO_DIR}} \
        --python_out={{COMMON_PROTO_DIR}} \
        `find {{PROTO_DIR}} -name "*.proto"`
    uv sync --all-packages
    uvx ruff check --select I --fix

clean:
    rm -rf {{COMMON_PROTO_DIR}}/common/protos
    mkdir -p {{COMMON_PROTO_DIR}}/common/protos

test target:
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --package {{target}} pytest

format:
    uvx ruff check --select I --fix

run-rts level="tutorial" output_directory="output":
    #!/usr/bin/env bash
    set -eou pipefail

    uv run engine --level {{level}}.json {{output_directory}} &
    engine_pid=$!
    trap 'kill $engine_pid 2>/dev/null || true' EXIT

    uv run gui-rts

run-llm level="tutorial" output_directory="output":
    #!/usr/bin/env bash
    set -eou pipefail

    uv run engine --level {{level}}.json {{output_directory}} &
    engine_pid=$!
    trap 'kill $engine_pid 2>/dev/null || true' EXIT

    uv run gui-llm 

make-levels:
    uv run python generate_level.py assets/levels/level1.json
    uv run python generate_level.py --castle_tile 8,5 assets/levels/level2.json
    uv run python generate_tutorial.py
