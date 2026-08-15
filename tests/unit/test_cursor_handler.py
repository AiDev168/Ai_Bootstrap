from pathlib import Path
from unittest.mock import Mock

from ai_engineering_bootstrap.executor.handlers.base import ExecutionContext
from ai_engineering_bootstrap.executor.handlers.system_handlers import (
    InstallCursorRealHandler,
)
from ai_engineering_bootstrap.executor.mode import ExecutionMode
from ai_engineering_bootstrap.executor.models import ExecutionStatus
from ai_engineering_bootstrap.planner.models import ExecutionPlanAction

API_URL = "https://www.cursor.com/api/download?platform=linux-x64&releaseTrack=stable"
DEB_URL = "https://downloads.cursor.com/production/cursor_3.15.6_amd64.deb"


def _action(**context: object) -> ExecutionPlanAction:
    return ExecutionPlanAction(
        action_id="install_cursor",
        description="Install Cursor",
        priority=1,
        context=context,
    )


def _context() -> ExecutionContext:
    return ExecutionContext(
        mode=ExecutionMode.REAL,
        dry_run=False,
        is_approved=True,
    )


def test_cursor_handler_resolves_official_deb_url_from_metadata() -> None:
    runner = Mock(return_value=Mock(returncode=0, stdout="", stderr=""))
    downloader = Mock()
    handler = InstallCursorRealHandler(runner=runner, downloader=downloader)
    handler._fetch_metadata = Mock(
        return_value={
            "downloadUrl": "https://downloads.cursor.com/cursor.AppImage",
            "debUrl": DEB_URL,
            "rpmUrl": "https://downloads.cursor.com/cursor.rpm",
            "version": "3.15.6",
        }
    )

    def write_package(url: str, destination: Path) -> None:
        assert url == DEB_URL
        destination.write_bytes(b"deb-package")

    downloader.side_effect = write_package
    result = handler.execute(_action(download_url=API_URL), _context())

    assert result.status == ExecutionStatus.SUCCESS
    assert runner.call_args.args[0] == (
        "sudo",
        "apt-get",
        "install",
        "-y",
        runner.call_args.args[0][-1],
    )
    downloaded_path = downloader.call_args.args[1]
    assert downloader.call_args.args[0] == DEB_URL
    assert Path(downloaded_path).name == "cursor.deb"


def test_cursor_handler_rejects_non_official_deb_url() -> None:
    runner = Mock()
    handler = InstallCursorRealHandler(runner=runner, downloader=Mock())
    handler._fetch_metadata = Mock(
        return_value={"debUrl": "https://example.com/cursor.deb"}
    )

    result = handler.execute(_action(), _context())

    assert result.status == ExecutionStatus.FAILED
    assert "approved official DEB" in result.message
    runner.assert_not_called()


def test_cursor_handler_does_not_treat_appimage_as_deb() -> None:
    runner = Mock()
    handler = InstallCursorRealHandler(runner=runner, downloader=Mock())
    handler._fetch_metadata = Mock(
        return_value={"downloadUrl": "https://downloads.cursor.com/cursor.AppImage"}
    )

    result = handler.execute(_action(), _context())

    assert result.status == ExecutionStatus.FAILED
    assert "DEB package" in result.message
    runner.assert_not_called()
