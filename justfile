# Justfile for working with the llm-mas-control project

PROTO_DIR := "protos"
COMMON_PROTO_DIR := "packages/common/src"
WEB_DIR := "packages/interfaces/web"

# Initialize the project
init:
    uv run python -m grpc_tools.protoc \
        -I={{PROTO_DIR}} \
        --python_out={{COMMON_PROTO_DIR}} \
        `find {{PROTO_DIR}} -name "*.proto"`
    uv sync --all-packages

clean:
    rm -rf {{COMMON_PROTO_DIR}}/common/protos
    mkdir -p {{COMMON_PROTO_DIR}}/common/protos

test target:
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --package {{target}} pytest

# Install the web frontend's npm dependencies
interfaces-install:
    cd {{WEB_DIR}} && npm install

# Run the backend (:8000, auto-reload) and the vite dev server (:5173) together
interfaces-dev:
    #!/usr/bin/env bash
    trap 'kill 0' EXIT
    uv run --package interfaces uvicorn interfaces.server:app --reload --port 8000 &
    cd {{WEB_DIR}} && npm run dev

# Build the frontend into web/dist so the backend can serve it
interfaces-build:
    cd {{WEB_DIR}} && npm install && npm run build

# Serve the built frontend and backend from one process on :8000
interfaces-serve:
    uv run --package interfaces interfaces

# Run the dummy engine as a separate process (use with INTERFACES_ENGINE=socket)
dummy-engine:
    uv run --package interfaces dummy-engine
