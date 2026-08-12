"""Tests for controlled real system handlers."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai_engineering_bootstrap.executor.handlers.base import ExecutionContext
from ai_engineering_bootstrap.executor.handlers.system_handlers import (
    InstallCursorRealHandler,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction


def _real_context() -> ExecutionContext:
    return ExecutionContext(ExecutionMode.REAL, dry_run=False, is_approved=True)


def _action() -> ExecutionPlanAction:
    return ExecutionPlanAction(
        "install_cursor",
        "Install Cursor",
        1,
        {},
    )


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def test_cursor_resolves_official_deb_url_from_api() -> None:
    api_url = InstallCursorRealHandler.API_URL.format(platform="linux-x64")
    package_url = "https://downloads.cursor.com/production/client/linux/x64/deb/Cursor-3.13.0-build.deb"
    response = _Response({"downloadUrl": package_url})

    handler = InstallCursorRealHandler()
    with patch(
        "ai_engineering_bootstrap.executor.handlers.system_handlers.urllib.request.urlopen",
        return_value=response,
    ) as opener:
        resolved = handler._resolve_download_url(api_url)

    assert resolved == package_url
    request = opener.call_args.args[0]
    assert request.full_url == api_url
    assert request.headers["User-agent"]
    assert opener.call_args.kwargs["timeout"] == 30


def test_cursor_prefers_official_deb_url() -> None:
    api_url = InstallCursorRealHandler.API_URL.format(platform="linux-x64")
    deb_url = "https://downloads.cursor.com/production/a/linux/x64/deb/cursor.deb"
    response = _Response(
        {
            "downloadUrl": "https://downloads.cursor.com/production/a/linux/x64/Cursor.AppImage",
            "debUrl": deb_url,
        }
    )

    handler = InstallCursorRealHandler()
    with patch(
        "ai_engineering_bootstrap.executor.handlers.system_handlers.urllib.request.urlopen",
        return_value=response,
    ):
        assert handler._resolve_download_url(api_url) == deb_url


def test_cursor_rejects_untrusted_resolved_url() -> None:
    response = _Response({"downloadUrl": "https://example.invalid/cursor.deb"})
    api_url = InstallCursorRealHandler.API_URL.format(platform="linux-x64")

    with patch(
        "ai_engineering_bootstrap.executor.handlers.system_handlers.urllib.request.urlopen",
        return_value=response,
    ):
        try:
            InstallCursorRealHandler()._resolve_download_url(api_url)
        except RuntimeError as exc:
            assert "official Cursor download endpoint" in str(exc)
        else:
            raise AssertionError("untrusted Cursor URL must be rejected")


def test_cursor_handler_downloads_resolved_package_url_without_shell(
    tmp_path: Path,
) -> None:
    package_url = "https://downloads.cursor.com/production/client/linux/x64/deb/Cursor-3.13.0-build.deb"
    downloader = MagicMock()
    runner = MagicMock()
    runner.return_value = SimpleNamespace(returncode=0, stdout="installed", stderr="")

    handler = InstallCursorRealHandler(runner=runner, downloader=downloader)

    with patch.object(
        handler,
        "_resolve_download_url",
        return_value=package_url,
    ):
        def write_package(url: str, destination: Path) -> None:
            assert url == package_url
            destination.write_bytes(b"debian-package")

        downloader.side_effect = write_package
        with patch(
            "ai_engineering_bootstrap.executor.handlers.system_handlers.platform.system",
            return_value="Linux",
        ), patch(
            "ai_engineering_bootstrap.executor.handlers.system_handlers.shutil.which",
            return_value="/usr/bin/tool",
        ):
            result = handler.execute(_action(), _real_context())

    assert result.status == ExecutionStatus.SUCCESS
    assert runner.call_args.args[0][0:4] == ("sudo", "apt-get", "install", "-y")
    assert runner.call_args.kwargs["shell"] is False
    downloader.assert_called_once_with(package_url, downloader.call_args.args[1])
