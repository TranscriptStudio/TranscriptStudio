"""
Tests du menu contextuel des projets recents
(et de SettingsManager.remove_recent_project).
"""

from pathlib import Path

from services.settings import SettingsManager


def _settings(tmp_path):
    return SettingsManager(app_folder=tmp_path)


def test_remove_recent_project_removes_entry(tmp_path):
    manager = _settings(tmp_path)

    project_a = tmp_path / "a.sttproj"
    project_a.touch()

    project_b = tmp_path / "b.sttproj"
    project_b.touch()

    manager.add_recent_project(str(project_a))
    manager.add_recent_project(str(project_b))

    assert len(manager.get_recent_projects()) == 2

    removed = manager.remove_recent_project(
        str(project_a)
    )

    assert removed is True
    assert manager.get_recent_projects() == [
        str(project_b)
    ]


def test_remove_recent_project_missing_entry(tmp_path):
    manager = _settings(tmp_path)

    removed = manager.remove_recent_project(
        str(tmp_path / "inconnu.sttproj")
    )

    assert removed is False
    assert manager.get_recent_projects() == []


def test_remove_recent_project_keeps_file_on_disk(tmp_path):
    """
    La suppression ne retire que la reference :
    le fichier .sttproj reste present.
    """

    manager = _settings(tmp_path)

    project = tmp_path / "garde.sttproj"
    project.touch()

    manager.add_recent_project(str(project))
    manager.remove_recent_project(str(project))

    assert project.is_file()
