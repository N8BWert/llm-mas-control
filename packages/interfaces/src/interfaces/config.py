"""
Settings for the interface backend, read from INTERFACES_* environment variables.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INTERFACES_")

    host: str = "127.0.0.1"
    port: int = 8000
    # Default UI mode when the URL has no ?mode=
    mode: Literal["rts", "llm"] = "rts"
    # "dummy" runs the dummy engine in-process; "socket" talks to an external engine
    engine: Literal["dummy", "socket"] = "dummy"
    scenario: Path = PACKAGE_ROOT / "scenarios" / "pilot.json"
    # Socket mode: the interface listens for GameState on state_port and the
    # engine listens for AgentActionRequest on action_port
    engine_host: str = "127.0.0.1"
    state_port: int = 5100
    action_port: int = 5101
    tick_hz: float = 15.0
    engine_hz: float = 30.0
    video_url: str = ""
    llm_model: str = "gpt-4o-mini"
    # Seconds between automatic LLM re-plans while robots sit idle
    llm_replan_s: float = 20.0
    web_dist: Path = PACKAGE_ROOT / "web" / "dist"


settings = Settings()
