"""Resolve declared audit labels independently of authorization."""
from dataclasses import dataclass
from pathlib import Path
import re
import tomllib

from django.conf import settings
from django.core.management.base import CommandError


@dataclass(frozen=True)
class Attribution:
    director: str
    agent: str

    def describe_cli(self):
        return f"Human director: {self.director}\nExecution agent: {self.agent}\nInterface: cli"


def _label(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,149}", value):
        raise ValueError(f"Invalid attribution {field}. Use a nonpersonal role identifier.")
    return value


def resolve_attribution(*, operator=None, agent=None):
    path = Path(settings.BASE_DIR) / ".rigarchive.toml"
    try:
        with path.open("rb") as stream:
            config = tomllib.load(stream)
    except FileNotFoundError:
        config = {}
    except (OSError, ValueError) as exc:
        raise ValueError("Cannot read valid .rigarchive.toml attribution configuration.") from exc
    attribution = config.get("attribution", {})
    if not isinstance(attribution, dict) or set(attribution) - {"director", "agent"}:
        raise ValueError("Invalid .rigarchive.toml attribution section.")
    director = _label(attribution.get("director", "project_owner"), "director")
    declared_agent = _label(attribution.get("agent", "codex"), "agent")
    return Attribution(
        director if operator is None else _label(operator, "director"),
        declared_agent if agent is None else _label(agent, "agent"),
    )


def add_attribution_arguments(parser):
    parser.add_argument("--operator", help="Declared human director role override.")
    parser.add_argument("--agent", help="Declared operation agent override.")


def cli_attribution(options):
    try:
        return resolve_attribution(operator=options.get("operator"), agent=options.get("agent"))
    except ValueError as exc:
        raise CommandError(str(exc)) from exc
