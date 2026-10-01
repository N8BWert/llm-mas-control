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

clean:
    rm -rf {{COMMON_PROTO_DIR}}/common/protos
    mkdir -p {{COMMON_PROTO_DIR}}/common/protos

test target:
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --package {{target}} pytest
