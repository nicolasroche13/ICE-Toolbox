from __future__ import annotations

import sys
from pathlib import Path

from app.core import paths


def test_is_frozen_false_in_dev(monkeypatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert paths.is_frozen() is False


def test_is_frozen_true_when_pyinstaller_sets_flag(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert paths.is_frozen() is True


def test_frozen_resource_root_uses_meipass_when_present(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.frozen_resource_root() == tmp_path


def test_frozen_resource_root_falls_back_to_executable_dir_for_onedir_builds(monkeypatch, tmp_path) -> None:
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    fake_exe = tmp_path / "EndpointToolbox.exe"
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert paths.frozen_resource_root() == tmp_path


def test_resource_path_dev_mode_resolves_relative_to_repo_root(monkeypatch) -> None:
    monkeypatch.setattr(paths, "is_frozen", lambda: False)
    resolved = paths.resource_path("app", "version.py")
    assert resolved.exists()
    assert resolved.name == "version.py"


def test_resource_path_frozen_mode_resolves_relative_to_meipass(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    monkeypatch.setattr(paths, "frozen_resource_root", lambda: tmp_path)
    resolved = paths.resource_path("resources", "windows", "app.ico")
    assert resolved == tmp_path / "resources" / "windows" / "app.ico"


def test_user_data_dir_windows_uses_appdata(monkeypatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    result = paths.user_data_dir()
    assert result == Path(r"C:\Users\test\AppData\Roaming") / "EndpointToolbox"


def test_user_data_dir_windows_without_appdata_falls_back(monkeypatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    result = paths.user_data_dir()
    assert result == Path.home() / "AppData" / "Roaming" / "EndpointToolbox"


def test_user_data_dir_macos_preserves_legacy_dotfile_location(monkeypatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    result = paths.user_data_dir()
    assert result == Path.home() / ".endpoint_toolbox"


def test_user_data_dir_linux_preserves_legacy_dotfile_location(monkeypatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "linux")
    result = paths.user_data_dir()
    assert result == Path.home() / ".endpoint_toolbox"


def test_user_data_dir_never_next_to_executable(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(paths, "is_frozen", lambda: True)
    fake_exe_dir = tmp_path / "Portable"
    monkeypatch.setattr(paths, "frozen_resource_root", lambda: fake_exe_dir)
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    result = paths.user_data_dir()
    assert fake_exe_dir not in result.parents
    assert result != fake_exe_dir


def test_user_log_dir_is_under_user_data_dir(monkeypatch) -> None:
    monkeypatch.setattr(paths.sys, "platform", "darwin")
    assert paths.user_log_dir() == paths.user_data_dir() / "logs"
