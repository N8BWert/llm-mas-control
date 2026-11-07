#!/usr/bin/env bash

set -eou pipefail

LEVEL=$1
OUTPUT_DIRECTORY=$2

uv run engine --level ${LEVEL} ${OUTPUT_DIRECTORY} &
engine_pid=$!
trap 'kill $engine_pid >/dev/null || true' EXIT

uv run gui-llm

