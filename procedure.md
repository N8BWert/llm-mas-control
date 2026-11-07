# User Testing Procedure

1) Boot up ./docker/python-backend/docker-run-user-code.sh
2) Source install/setup.bash
3) install uv
4) cd `/user_code_python/nate/llm-mas-control`
5) remove uv.lock
6) run `uv sync --all-packages`
7) run `./run-llm.sh <level> <output_directory>` or `./run-rts.sh <level> <output_directory>`
