import os

from app.config import CATEGORIES
from unittest.mock import patch
from app.scanner import (
    get_log_locations,
    get_system_locations,
)
from pathlib import Path
from datetime import datetime

from app.service import (
    analyze_folder,
    clean_folder,
    empty_recycle_bin,
    analyze_system,
    clean_system,
)


def make_file_old(file: Path, hours: int = 25):
    """Make a test file appear older than the required age."""
    old_time = datetime.now().timestamp() - (hours * 60 * 60)
    os.utime(file, (old_time, old_time))


def test_analyze_folder(tmp_path):
    file_1 = tmp_path / "archivo.tmp"
    file_1.write_text("Hello")

    file_2 = tmp_path / "document.txt"
    file_2.write_text("World")

    result = analyze_folder(tmp_path)

    assert result["files"] == 2
    assert result["size"] == 10


def test_clean_folder(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("Hello")
    make_file_old(file)

    result = clean_folder(tmp_path)

    assert result["deleted"] == 1


def test_empty_recycle_bin():
    with patch(
        "app.service.cleaner_empty_recycle_bin",
        return_value={"success": True},
    ):
        result = empty_recycle_bin()

    assert result["success"] is True


def test_analyze_system(tmp_path, monkeypatch):
    temp_location = tmp_path / "temp"
    cache_location = tmp_path / "cache"
    logs_location = tmp_path / "logs"

    temp_location.mkdir()
    cache_location.mkdir()
    logs_location.mkdir()

    temp_file_1 = temp_location / "a.tmp"
    temp_file_1.write_text("12345")
    make_file_old(temp_file_1)

    temp_file_2 = temp_location / "b.tmp"
    temp_file_2.write_text("12345")
    make_file_old(temp_file_2)

    cache_file = cache_location / "c.cache"
    cache_file.write_text("1234567890")
    make_file_old(cache_file)

    log_file = logs_location / "app.log"
    log_file.write_text("123")
    make_file_old(log_file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [temp_location],
            "cache": [cache_location],
            "logs": [logs_location],
        },
    )

    result = analyze_system()

    assert result["categories"]["temporary"]["files"] == 2
    assert result["categories"]["temporary"]["size"] == 10

    assert result["categories"]["cache"]["files"] == 1
    assert result["categories"]["cache"]["size"] == 10

    assert result["categories"]["logs"]["files"] == 1
    assert result["categories"]["logs"]["size"] == 3

    assert result["total"]["files"] == 4
    assert result["total"]["size"] == 23


def test_analyze_system_only_counts_cleanable_files(
    tmp_path,
    monkeypatch,
):
    temp_location = tmp_path / "temp"
    temp_location.mkdir()

    clean_file = temp_location / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    normal_file = temp_location / "document.txt"
    normal_file.write_text("Hello World")

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [temp_location],
            "cache": [],
            "logs": [],
        },
    )

    result = analyze_system()

    assert result["categories"]["temporary"]["files"] == 1
    assert result["categories"]["temporary"]["size"] == 5

    assert result["total"]["files"] == 1
    assert result["total"]["size"] == 5


def test_categories_configuration():
    assert ".tmp" in CATEGORIES["temporary"]
    assert ".temp" in CATEGORIES["temporary"]
    assert ".cache" in CATEGORIES["cache"]
    assert ".log" in CATEGORIES["logs"]


def test_get_log_locations(monkeypatch):
    monkeypatch.setenv(
        "LOCALAPPDATA",
        "C:/Users/test/AppData/Local",
    )

    locations = get_log_locations()

    assert locations == [
        Path("C:/Users/test/AppData/Local") / "Logs"
    ]


def test_get_system_locations(monkeypatch):
    monkeypatch.setattr(
        "app.scanner.get_temporary_locations",
        lambda: [Path("C:/temp")],
    )

    monkeypatch.setattr(
        "app.scanner.get_cache_locations",
        lambda: [Path("C:/cache")],
    )

    monkeypatch.setattr(
        "app.scanner.get_log_locations",
        lambda: [Path("C:/logs")],
    )

    locations = get_system_locations()

    assert locations == {
        "temporary": [Path("C:/temp")],
        "cache": [Path("C:/cache")],
        "logs": [Path("C:/logs")],
    }


def test_analyze_system_uses_system_locations(
    tmp_path,
    monkeypatch,
):
    temp_location = tmp_path / "temp"
    temp_location.mkdir()

    file = temp_location / "archivo.tmp"
    file.write_text("Hello")
    make_file_old(file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [temp_location],
            "cache": [],
            "logs": [],
        },
    )

    result = analyze_system()

    assert result["categories"]["temporary"]["files"] == 1
    assert result["categories"]["temporary"]["size"] == 5
    assert result["total"]["files"] == 1
    assert result["total"]["size"] == 5


def test_clean_system(tmp_path, monkeypatch):
    temp_location = tmp_path / "temp"
    temp_location.mkdir()

    clean_file = temp_location / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    normal_file = temp_location / "document.txt"
    normal_file.write_text("Hello World")

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [temp_location],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = analyze_system()

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert result["skipped"] == 0
    assert result["errors"] == 0

    assert not clean_file.exists()
    assert normal_file.exists()


def test_clean_system_uses_analysis_items(
    tmp_path,
    monkeypatch,
):
    clean_file = tmp_path / "archivo.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [tmp_path],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = {
        "categories": {
            "temporary": {
                "files": 1,
                "size": 5,
                "items": [clean_file],
            },
            "cache": {
                "files": 0,
                "size": 0,
                "items": [],
            },
            "logs": {
                "files": 0,
                "size": 0,
                "items": [],
            },
        },
        "total": {
            "files": 1,
            "size": 5,
        },
    }

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert result["skipped"] == 0
    assert result["errors"] == 0
    assert not clean_file.exists()


def test_analyze_system_returns_cleanable_items(
    tmp_path,
    monkeypatch,
):
    temp_location = tmp_path / "temp"
    temp_location.mkdir()

    clean_file = temp_location / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    normal_file = temp_location / "document.txt"
    normal_file.write_text("Hello World")

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [temp_location],
            "cache": [],
            "logs": [],
        },
    )

    result = analyze_system()

    assert result["categories"]["temporary"]["files"] == 1

    assert result["categories"]["temporary"]["size"] == 5

    assert result["categories"]["temporary"]["items"] == [
        clean_file
    ]

    assert result["total"]["files"] == 1
    assert result["total"]["size"] == 5


def test_clean_system_does_not_delete_files_added_after_analysis(
    tmp_path,
    monkeypatch,
):
    clean_file = tmp_path / "archivo.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [tmp_path],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = {
        "categories": {
            "temporary": {
                "files": 1,
                "size": 5,
                "items": [clean_file],
            },
            "cache": {
                "files": 0,
                "size": 0,
                "items": [],
            },
            "logs": {
                "files": 0,
                "size": 0,
                "items": [],
            },
        },
        "total": {
            "files": 1,
            "size": 5,
        },
    }

    new_file = tmp_path / "nuevo.tmp"
    new_file.write_text("New file")

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
    )

    assert not clean_file.exists()
    assert new_file.exists()

    assert result["deleted"] == 1
    assert result["freed"] == 5


def test_clean_system_respects_protection_added_after_analysis(
    tmp_path,
    monkeypatch,
):
    clean_file = tmp_path / "archivo.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [tmp_path],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = {
        "categories": {
            "temporary": {
                "files": 1,
                "size": 5,
                "items": [clean_file],
            },
            "cache": {
                "files": 0,
                "size": 0,
                "items": [],
            },
            "logs": {
                "files": 0,
                "size": 0,
                "items": [],
            },
        },
        "total": {
            "files": 1,
            "size": 5,
        },
    }

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
        protected=[clean_file],
    )

    assert clean_file.exists()
    assert result["deleted"] == 0
    assert result["freed"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == 0


def test_clean_system_skips_recent_file(
    tmp_path,
    monkeypatch,
):
    file = tmp_path / "archivo.tmp"
    file.write_text("Hello")

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [tmp_path],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = {
        "categories": {
            "temporary": {
                "files": 1,
                "size": 5,
                "items": [file],
            },
            "cache": {
                "files": 0,
                "size": 0,
                "items": [],
            },
            "logs": {
                "files": 0,
                "size": 0,
                "items": [],
            },
        },
        "total": {
            "files": 1,
            "size": 5,
        },
    }

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 0
    assert result["skipped"] == 1
    assert file.exists()


def test_clean_system_cleans_old_file(
    tmp_path,
    monkeypatch,
):
    file = tmp_path / "archivo.tmp"
    file.write_text("Hello")
    make_file_old(file)

    monkeypatch.setattr(
        "app.service.get_system_locations",
        lambda: {
            "temporary": [tmp_path],
            "cache": [],
            "logs": [],
        },
    )

    analysis_result = {
        "categories": {
            "temporary": {
                "files": 1,
                "size": 5,
                "items": [file],
            },
            "cache": {
                "files": 0,
                "size": 0,
                "items": [],
            },
            "logs": {
                "files": 0,
                "size": 0,
                "items": [],
            },
        },
        "total": {
            "files": 1,
            "size": 5,
        },
    }

    result = clean_system(
        analysis_result,
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert not file.exists()
