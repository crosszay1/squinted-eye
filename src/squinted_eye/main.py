from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

import yaml

from squinted_eye.lib.logger import logger

app_logger = logger(name="main")


def load_config(config_path: Path) -> dict[str, Any]:
	if not config_path.exists():
		raise FileNotFoundError(
			f"Config file not found at {config_path}. Create it from example-config.yaml."
		)

	with config_path.open("r", encoding="utf-8") as config_file:
		config = yaml.safe_load(config_file) or {}

	if not isinstance(config, dict):
		raise ValueError("config.yaml must parse to a mapping/object.")

	return config


def normalize_monitor_settings(settings: dict[str, Any]) -> dict[str, Any]:
	normalized = dict(settings)

	# Allow config key name used in example-config.yaml.
	if "read_interval" in normalized and "interval" not in normalized:
		normalized["interval"] = normalized.pop("read_interval")

	return normalized


def resolve_monitor_callable(monitor_name: str) -> Callable[..., Any]:
	monitor_slug = monitor_name.removesuffix("_monitor")
	module_name = f"squinted_eye.monitors.{monitor_slug}.main"

	try:
		module = import_module(module_name)
	except ModuleNotFoundError as exc:
		raise ModuleNotFoundError(
			f"Monitor module '{module_name}' could not be imported for '{monitor_name}'."
		) from exc

	monitor_callable = getattr(module, monitor_name, None)

	if monitor_callable is None:
		raise AttributeError(
			f"Monitor '{monitor_name}' was not found in module '{module_name}'."
		)

	return monitor_callable


async def run_enabled_monitors(config: dict[str, Any]) -> None:
	enabled_monitors = config.get("enabled_monitors", [])
	all_settings = config.get("settings", {})

	if not enabled_monitors:
		app_logger.warning("No monitors are enabled in config.yaml.")
		return

	monitor_tasks = []

	for monitor_name in enabled_monitors:
		if not isinstance(monitor_name, str):
			app_logger.error("Skipping non-string monitor name: %r", monitor_name)
			continue

		raw_settings = all_settings.get(monitor_name, {})
		if not isinstance(raw_settings, dict):
			app_logger.error("Settings for %s must be a mapping/object.", monitor_name)
			continue

		settings = normalize_monitor_settings(raw_settings)

		try:
			monitor_callable = resolve_monitor_callable(monitor_name)
			monitor_tasks.append(monitor_callable(**settings))
			app_logger.info("Queued monitor: %s", monitor_name)
		except (ModuleNotFoundError, AttributeError, TypeError) as exc:
			app_logger.error("Failed to load monitor '%s': %s", monitor_name, exc)

	if not monitor_tasks:
		app_logger.warning("No monitor tasks were created from config.")
		return

	await asyncio.gather(*monitor_tasks)


def main() -> None:
	project_root = Path(__file__).resolve().parents[2]
	config_path = project_root / "config.yaml"

	try:
		config = load_config(config_path)
		asyncio.run(run_enabled_monitors(config))
	except Exception as exc:  # Keep top-level failure visible and logged.
		app_logger.exception("Application startup failed: %s", exc)
		raise