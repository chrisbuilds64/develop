"""Configuration loading.

Gatehouse refuses to start on an incomplete configuration rather than
falling back to a default. A silent default here would mean an operator
sitting with a client, believing a pack is loaded that is not.

Models are configured as named profiles, and tasks are mapped onto
profiles. A client can therefore run cheap follow-up questions on a
small local model and a final synthesis on a large hosted one, or route
everything to one endpoint, without touching code.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

# Every task Gatehouse can route to a model. Named here so a typo in the
# configuration is caught at startup rather than in front of a client.
TASKS = ("followup",)


class ConfigError(Exception):
    """Raised with a message meant for an operator, not a stack trace."""


@dataclass(frozen=True)
class ModelProfile:
    name: str
    adapter: str
    destination: str
    local: bool = False
    model: str | None = None
    api_key_env: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class Config:
    pack_path: Path
    instance_path: Path
    profiles: dict[str, ModelProfile]
    default_profile: str
    task_profiles: dict[str, str]
    host: str
    port: int

    def profile_for(self, task: str) -> ModelProfile:
        return self.profiles[self.task_profiles.get(task, self.default_profile)]

    @property
    def destinations(self) -> list[str]:
        """Every distinct destination this configuration can reach.

        What the client is told. One profile or five, the answer to
        'where do our answers go' must be complete.
        """
        used = {self.task_profiles.get(t, self.default_profile) for t in TASKS}
        seen, out = set(), []
        for name in sorted(used):
            profile = self.profiles[name]
            label = profile.destination + (" (im Haus)" if profile.local else "")
            if label not in seen:
                seen.add(label)
                out.append(label)
        return out


def load(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(
            f"No configuration at {path}. Copy gatehouse.example.toml to "
            f"{path.name} and set the pack and instance paths."
        )

    with path.open("rb") as fh:
        raw = tomllib.load(fh)

    base = path.parent

    pack_path = _required_path(raw, "pack", "path", base)
    if not pack_path.is_dir():
        raise ConfigError(
            f"Pack directory not found: {pack_path}. The canon pack is not "
            "part of this repository and must be supplied separately."
        )

    instance_path = _required_path(raw, "instance", "path", base)
    instance_path.mkdir(parents=True, exist_ok=True)

    model_raw = raw.get("model", {})
    profiles = _profiles(model_raw.get("profiles", {}))

    default_profile = model_raw.get("default")
    if not default_profile:
        raise ConfigError("[model] default is required and must name a profile.")
    if default_profile not in profiles:
        raise ConfigError(
            f"[model] default names '{default_profile}', which is not a "
            f"profile. Defined: {', '.join(sorted(profiles)) or 'none'}."
        )

    task_profiles = dict(model_raw.get("tasks", {}))
    for task, profile_name in task_profiles.items():
        if task not in TASKS:
            raise ConfigError(
                f"[model.tasks] '{task}' is not a task Gatehouse runs. "
                f"Known tasks: {', '.join(TASKS)}."
            )
        if profile_name not in profiles:
            raise ConfigError(
                f"[model.tasks] {task} points at profile '{profile_name}', "
                f"which is not defined. Defined: {', '.join(sorted(profiles))}."
            )

    server = raw.get("server", {})

    return Config(
        pack_path=pack_path,
        instance_path=instance_path,
        profiles=profiles,
        default_profile=default_profile,
        task_profiles=task_profiles,
        host=server.get("host", "127.0.0.1"),
        port=int(server.get("port", 8100)),
    )


def _profiles(raw: dict) -> dict[str, ModelProfile]:
    if not raw:
        raise ConfigError(
            "No [model.profiles.<name>] section defined. At least one model "
            "profile is required, even if it is the 'echo' adapter."
        )

    profiles: dict[str, ModelProfile] = {}
    for name, entry in raw.items():
        adapter = entry.get("adapter")
        if not adapter:
            raise ConfigError(f"[model.profiles.{name}] adapter is required.")
        destination = entry.get("destination")
        if not destination:
            raise ConfigError(
                f"[model.profiles.{name}] destination is required. It is what "
                "the client is told about where their answers go, so it has "
                "to be written by hand."
            )
        profiles[name] = ModelProfile(
            name=name,
            adapter=adapter,
            destination=destination,
            local=bool(entry.get("local", False)),
            model=entry.get("model"),
            api_key_env=entry.get("api_key_env"),
            base_url=entry.get("base_url"),
        )
    return profiles


def _required_path(raw: dict, section: str, key: str, base: Path) -> Path:
    value = raw.get(section, {}).get(key)
    if not value:
        raise ConfigError(f"[{section}] {key} is required.")
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (base / candidate).resolve()
    return candidate
