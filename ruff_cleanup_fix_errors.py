from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(".")


def replace(path: str, old: str, new: str, count: int | None = None) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    updated = text.replace(old, new, -1 if count is None else count)
    if updated == text:
        raise SystemExit(f"Pattern not found: {path}: {old!r}")
    p.write_text(updated, encoding="utf-8")


def regex_replace(path: str, pattern: str, repl: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    updated, n = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if not n:
        raise SystemExit(f"Regex not found: {path}: {pattern!r}")
    p.write_text(updated, encoding="utf-8")


# Timezone-aware UTC.
for path in [
    "src/ai_engineering_bootstrap/backend/api.py",
    "src/ai_engineering_bootstrap/environment/session_models.py",
    "src/ai_engineering_bootstrap/environment/session_store.py",
]:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    text = re.sub(r"^from datetime import .*\n", "", text, flags=re.MULTILINE)
    text = "from datetime import datetime, timezone\n" + text
    text = text.replace("datetime.utcnow()", "datetime.now(timezone.utc)")
    text = text.replace("datetime.now(UTC)", "datetime.now(timezone.utc)")
    text = text.replace(
        "default_factory=datetime.utcnow",
        "default_factory=lambda: datetime.now(timezone.utc)",
    )
    p.write_text(text, encoding="utf-8")

# Async endpoint must not perform blocking file I/O.
p = ROOT / "src/ai_engineering_bootstrap/backend/api.py"
text = p.read_text(encoding="utf-8")
text = text.replace("async def serve_gui():", "def serve_gui():")
text = text.replace("    import os\n", "", 1)
p.write_text(text, encoding="utf-8")

# Intent/recovery/planner broad catches are deliberate LLM fallback boundaries.
for path in {
    "src/ai_engineering_bootstrap/agent/intent_parser.py": [
        "        except Exception:\n",
    ],
    "src/ai_engineering_bootstrap/agent/recovery_agent.py": [
        "        except Exception:\n",
    ],
    "src/ai_engineering_bootstrap/agent/strategy_planner.py": [
        "        except Exception:\n",
    ],
}:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    text = text.replace(
        "        except Exception:\n",
        "        except Exception:  # noqa: BLE001 - intentional LLM fallback boundary\n",
    )
    p.write_text(text, encoding="utf-8")

# API route boundaries deliberately convert unexpected application errors to HTTP responses.
p = ROOT / "src/ai_engineering_bootstrap/backend/api.py"
text = p.read_text(encoding="utf-8")
if "import logging\n" not in text:
    text = text.replace("import os\n", "import os\nimport logging\n", 1)
if "logger = logging.getLogger(__name__)\n" not in text:
    marker = 'API_VERSION = "v1"\n'
    text = text.replace(marker, marker + "\nlogger = logging.getLogger(__name__)\n", 1)
text = text.replace(
    "except Exception as e:\n",
    "except Exception as e:  # noqa: BLE001 - API boundary normalization\n",
)
text = text.replace(
    "except Exception:\n",
    "except Exception:  # noqa: BLE001 - API/WebSocket boundary\n",
)
text = text.replace(
    "            data = await websocket.receive_text()\n",
    "            await websocket.receive_text()\n",
)
text = text.replace(
    "    except Exception:  # noqa: BLE001 - API/WebSocket boundary\n        pass\n",
    '    except Exception:\n        logger.exception("Unexpected WebSocket failure for session %s", session_id)\n',
)
text = text.replace(
    '    except Exception: # noqa: BLE001 - API/WebSocket boundary\n        logger.exception("Unexpected WebSocket failure for session %s", session_id)\n',
    '    except Exception:\n        logger.exception("Unexpected WebSocket failure for session %s", session_id)\n',
)
text = text.replace('        api_url = settings.get("api_url", "")\n', "")
p.write_text(text, encoding="utf-8")

# Environment exports and typing.
p = ROOT / "src/ai_engineering_bootstrap/environment/__init__.py"
text = p.read_text(encoding="utf-8")
if '"DuplicateToolError"' not in text:
    text = text.replace(
        '    "ToolCatalog",\n', '    "DuplicateToolError",\n    "ToolCatalog",\n'
    )
# Keep a deterministic alphabetical __all__ to satisfy RUF022.
match = re.search(r"__all__\s*=\s*\[(.*?)\n\]", text, flags=re.DOTALL)
if match:
    entries = re.findall(r'"[^"]+"', match.group(1))
    sorted_entries = sorted(dict.fromkeys(entries))
    replacement = (
        "__all__ = [\n" + "".join(f"    {entry},\n" for entry in sorted_entries) + "]"
    )
    text = text[: match.start()] + replacement + text[match.end() :]
p.write_text(text, encoding="utf-8")

# Reconciler typing and nested conditional.
p = ROOT / "src/ai_engineering_bootstrap/environment/reconciler.py"
text = p.read_text(encoding="utf-8")
import_block = "from ai_engineering_bootstrap.environment.models import ("
if "    ToolRequirement,\n" not in text.split(")", 1)[0]:
    text = text.replace(import_block, import_block + "\n    ToolRequirement,", 1)
text = text.replace(
    "            elif pkg_req.version_constraint:\n                if not self._version_satisfies(actual_version, pkg_req.version_constraint):",
    "            elif pkg_req.version_constraint and not self._version_satisfies(actual_version, pkg_req.version_constraint):",
)
p.write_text(text, encoding="utf-8")

# Combine nested context managers in installation strategy.
p = ROOT / "src/ai_engineering_bootstrap/environment/installation_strategies.py"
text = p.read_text(encoding="utf-8")
text = text.replace(
    '                with urllib.request.urlopen(request, timeout=300) as response:\n                    with open(deb_path, "wb") as f:',
    '                with urllib.request.urlopen(request, timeout=300) as response, open(deb_path, "wb") as f:',
)
p.write_text(text, encoding="utf-8")

# Session store nested condition.
p = ROOT / "src/ai_engineering_bootstrap/environment/session_store.py"
text = p.read_text(encoding="utf-8")
text = text.replace(
    "            if session:\n                if status_filter is None or session.status == status_filter:",
    "            if session and (status_filter is None or session.status == status_filter):",
)
p.write_text(text, encoding="utf-8")

print("Ruff cleanup transformations applied.")
