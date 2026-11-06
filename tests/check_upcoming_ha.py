"""Import the integration inside an upcoming Home Assistant and report deprecations.

Run it inside a Home Assistant image with the repository mounted on /w:

    docker run --rm -v "$PWD:/w:ro" ghcr.io/home-assistant/home-assistant:beta \
        python /w/tests/check_upcoming_ha.py

Deprecations of entity properties (like the climate native_* rename in
Home Assistant 2026.11) are reported when the class is created, so importing
the platforms is enough to see them; no running Home Assistant and no Ebeco
account is needed. Exits 1 on an import error or on any deprecation report
that mentions ebeco. The pytest suite can't run inside the image because
pytest-homeassistant-custom-component pins the previous Home Assistant.
"""

import importlib
import logging
import pathlib
import sys
import warnings

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ["", ".const", ".data_handler", ".entity", ".config_flow", ".sensor", ".climate"]


class CollectWarnings(logging.Handler):
    """Keep every WARNING+ log record."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def main() -> int:
    sys.path.insert(0, str(REPO_ROOT))
    handler = CollectWarnings()
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.WARNING)

    from homeassistant.const import __version__  # noqa: PLC0415

    print(f"Home Assistant {__version__}")
    problems: list[str] = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for suffix in MODULES:
            name = f"custom_components.ebeco{suffix}"
            try:
                importlib.import_module(name)
                print(f"imported {name}")
            except Exception as err:  # noqa: BLE001 - report whatever broke the import
                problems.append(f"{name}: {type(err).__name__}: {err}")

    for record in handler.records:
        message = record.getMessage()
        if "ebeco" in message.lower() or record.name.startswith("custom_components.ebeco"):
            line = f"{record.levelname} {record.name}: {message}"
            print(line)
            if "deprecat" in message.lower():
                problems.append(line)
    for warning in caught:
        if "ebeco" in str(warning.filename):
            line = f"{warning.category.__name__} {warning.filename}:{warning.lineno}: {warning.message}"
            print(line)
            problems.append(line)

    if problems:
        print(f"\n{len(problems)} problem(s) against Home Assistant {__version__}:")
        for problem in problems:
            print(f" - {problem}")
        return 1
    print(f"\nOK against Home Assistant {__version__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
