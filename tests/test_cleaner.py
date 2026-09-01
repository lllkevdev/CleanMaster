import os
import pytest

from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.cleaner import (
    clean_files,
    is_protected,
    is_cleanable,
    cleanup_folder,
    is_protected_location,
    is_category_selected,
    should_clean,
    is_old_enough,
)

from app.scanner import (
    get_files,
    get_category,
    is_cache_location,
    get_cache_locations,
    get_temporary_locations,
    is_temporary_location,
)


def make_file_old(file: Path, hours: int = 25):
    """Make a test file appear older than the required age."""
    old_time = datetime.now().timestamp() - (hours * 60 * 60)
    os.utime(file, (old_time, old_time))


def test_clean_files(tmp_path):
    archive1 = tmp_path / "archivo1.txt"
    archive1.write_text("Hello")

    archive2 = tmp_path / "archivo2.txt"
    archive2.write_text("Hello")

    archive3 = tmp_path / "archivo3.txt"
    archive3.write_text("Hello")

    files = get_files(tmp_path)

    result = clean_files(files)

    assert result["deleted"] == 3
    assert result["freed"] == 15

    files = get_files(tmp_path)

    assert len(files) == 0


def test_clean_empty_folder():
    result = clean_files([])

    assert result["deleted"] == 0
    assert result["freed"] == 0


def test_clean_files_permission_error(tmp_path):
    archive1 = tmp_path / "archivo1.txt"
    archive1.write_text("Hello")

    files = get_files(tmp_path)

    with patch.object(Path, "unlink", side_effect=PermissionError):
        result = clean_files(files)

    assert result["deleted"] == 0
    assert result["freed"] == 0


def test_clean_files_not_found(tmp_path):
    archive1 = tmp_path / "archive.txt"
    archive1.write_text("Hello")

    files = get_files(tmp_path)

    with patch.object(Path, "unlink", side_effect=FileNotFoundError):
        result = clean_files(files)

    assert result["deleted"] == 0
    assert result["freed"] == 0


def test_clean_files_recursive(tmp_path):
    archive1 = tmp_path / "archive1.txt"
    archive1.write_text("Hello")

    subfolder = tmp_path / "cache"
    subfolder.mkdir()

    archive2 = subfolder / "archive2.txt"
    archive2.write_text("Hello")

    archive3 = subfolder / "archive3.txt"
    archive3.write_text("Hello")

    files = [
        archive1,
        archive2,
        archive3,
    ]

    result = clean_files(files)

    assert result["deleted"] == 3
    assert result["freed"] == 15

    assert not archive1.exists()
    assert not archive2.exists()
    assert not archive3.exists()


def test_clean_files_keeps_directories(tmp_path):
    archive1 = tmp_path / "archive1.txt"
    archive1.write_text("Hello")

    subfolder = tmp_path / "cache"
    subfolder.mkdir()

    archive2 = subfolder / "archive2.txt"
    archive2.write_text("Hello")

    archive3 = subfolder / "archive3.txt"
    archive3.write_text("Hello")

    files = [
        archive1,
        archive2,
        archive3,
    ]

    result = clean_files(files)

    assert result["deleted"] == 3
    assert result["freed"] == 15

    assert subfolder.exists()
    assert subfolder.is_dir()


def test_clean_files_stat_not_found():
    fake_file = MagicMock()
    fake_file.stat.side_effect = FileNotFoundError

    with patch("app.cleaner.get_files", return_value=[fake_file]):
        result = clean_files([fake_file])

    assert result["deleted"] == 0
    assert result["freed"] == 0


def test_is_protected(tmp_path):
    archive = tmp_path / "archive.txt"
    protected = tmp_path / "important.txt"

    assert is_protected(protected, [protected])
    assert not is_protected(archive, [protected])


def test_is_protected_rteturns_false():
    archive = Path("normal.txt")
    protected = [Path("important.txt")]

    result = is_protected(archive, protected)

    assert result is False


def test_is_cleanable_tmp_file():
    archive = Path("cache.tmp")

    result = is_cleanable(archive)

    assert result is True


def test_is_cleanable_non_tmp_file():
    archive = Path("document.txt")

    result = is_cleanable(archive)

    assert result is False


def test_clean_files_list(tmp_path):
    archive1 = tmp_path / "archive1.txt"
    archive1.write_text("Hello")

    archive2 = tmp_path / "archive2.txt"
    archive2.write_text("Hello")

    result = clean_files([archive1, archive2])

    assert result["deleted"] == 2
    assert result["freed"] == 10

    assert not archive1.exists()
    assert not archive2.exists()


def test_clean_files_integration(tmp_path):
    clean_file = tmp_path / "cache.tmp"
    clean_file.write_text("Hello")

    normal_file = tmp_path / "document.txt"
    normal_file.write_text("Hello")

    protected_file = tmp_path / "important.tmp"
    protected_file.write_text("Hello")

    files = get_files(tmp_path)

    protected = [protected_file]

    cleanable_files = [
        file
        for file in files
        if is_cleanable(file) and not is_protected(file, protected)
    ]

    result = clean_files(cleanable_files)

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not clean_file.exists()
    assert normal_file.exists()
    assert protected_file.exists()


def test_cleanup_folder(tmp_path):
    clean_file = tmp_path / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    normal_file = tmp_path / "document.txt"
    normal_file.write_text("Hello")

    protected_file = tmp_path / "important.tmp"
    protected_file.write_text("Hello")

    result = cleanup_folder(tmp_path, protected=[protected_file])

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not clean_file.exists()
    assert normal_file.exists()
    assert protected_file.exists()


def test_cleanup_folder_not_found(tmp_path):
    folder = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        cleanup_folder(folder)


def test_cleanup_folder_path_is_file(tmp_path):
    file = tmp_path / "archivo.txt"
    file.write_text("Hello")

    with pytest.raises(NotADirectoryError):
        cleanup_folder(file)


def test_cleanup_folder_protected(tmp_path):
    clean_file = tmp_path / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    protected_file = tmp_path / "important.tmp"
    protected_file.write_text("Hello")

    result = cleanup_folder(
        tmp_path,
        protected=[protected_file],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not clean_file.exists()
    assert protected_file.exists()


def test_cleanup_folder_only_cleanable(tmp_path):
    clean_file = tmp_path / "cache.tmp"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    normal_file = tmp_path / "document.txt"
    normal_file.write_text("Hello")

    result = cleanup_folder(tmp_path)

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not clean_file.exists()
    assert normal_file.exists()


def test_is_protected_location(tmp_path):
    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    file = protected_location / "cache.tmp"
    file.write_text("Hello")

    protected_locations = [protected_location]

    assert is_protected_location(file, protected_locations)


def test_is_protected_location_subfolder(tmp_path):
    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    subfolder = protected_location / "cache"
    subfolder.mkdir()

    file = subfolder / "cache.tmp"
    file.write_text("Hello")

    protected_locations = [protected_location]

    assert is_protected_location(file, protected_locations)


def test_is_not_protected_location(tmp_path):
    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    normal_location = tmp_path / "normal"
    normal_location.mkdir()

    file = normal_location / "cache.tmp"
    file.write_text("Hello")

    protected_locations = [protected_location]

    assert not is_protected_location(file, protected_locations)


def test_cleanup_folder_protected_location(tmp_path):
    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    file = protected_location / "cache.tmp"
    file.write_text("Hello")

    result = cleanup_folder(
        tmp_path,
        protected_locations=[protected_location],
    )

    assert result["deleted"] == 0
    assert result["freed"] == 0

    assert file.exists()


def test_is_category_selected():
    selected_categories = ["temporary", "cache"]

    assert is_category_selected("temporary", selected_categories)


def test_is_category_not_selected():
    selected_categories = ["temporary", "cache"]

    assert not is_category_selected("logs", selected_categories)


def test_get_category_temporary(tmp_path):
    file = tmp_path / "cache.tmp"
    file.write_text("Hello")

    assert get_category(file) == "temporary"


def test_should_clean_selected_category(tmp_path):
    file = tmp_path / "cache.tmp"
    file.write_text("Hello")
    make_file_old(file)

    selected_categories = ["temporary"]

    assert should_clean(file, selected_categories)


def test_should_not_clean_unselected_category(tmp_path):
    file = tmp_path / "server.log"
    file.write_text("Hello")

    selected_categories = ["temporary"]

    assert not should_clean(file, selected_categories)


def test_cleanup_folder_selected_categories(tmp_path):
    temporary_file = tmp_path / "cache.tmp"
    temporary_file.write_text("Hello")
    make_file_old(temporary_file)

    log_file = tmp_path / "server.log"
    log_file.write_text("Hello")

    result = cleanup_folder(
        tmp_path,
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not temporary_file.exists()
    assert log_file.exists()


def test_cleanup_folder_selected_category_respects_protected_location(tmp_path):
    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    file = protected_location / "cache.tmp"
    file.write_text("Hello")
    make_file_old(file)

    result = cleanup_folder(
        tmp_path,
        protected_locations=[protected_location],
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 0
    assert result["freed"] == 0
    assert file.exists()


def test_cleanup_folder_selected_category_respects_protected_file(tmp_path):
    temporary_file = tmp_path / "cache.tmp"
    temporary_file.write_text("Hello")
    make_file_old(temporary_file)

    protected_file = tmp_path / "important.tmp"
    protected_file.write_text("Hello")

    result = cleanup_folder(
        tmp_path,
        protected=[protected_file],
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not temporary_file.exists()
    assert protected_file.exists()


def test_get_category_cache(tmp_path):
    file = tmp_path / "cache.cache"
    file.write_text("Hello")

    assert get_category(file) == "cache"


def test_is_cache_location(tmp_path):
    cache_location = tmp_path / "cache"
    cache_location.mkdir()

    file = cache_location / "image.dat"
    file.write_text("Hello")

    assert is_cache_location(file, [cache_location])


def test_is_not_cache_location(tmp_path):
    cache_location = tmp_path / "cache"
    cache_location.mkdir()

    normal_location = tmp_path / "documents"
    normal_location.mkdir()

    file = normal_location / "document.dat"
    file.write_text("Hello")

    assert not is_cache_location(file, [cache_location])


def test_get_category_from_cache_location(tmp_path):
    cache_location = tmp_path / "cache"
    cache_location.mkdir()

    file = cache_location / "image.dat"
    file.write_text("Hello")

    cache_locations = [cache_location]

    assert get_category(file, cache_locations) == "cache"


def test_get_cache_locations():
    locations = get_cache_locations()

    assert isinstance(locations, list)


def test_get_cache_locations_returns_paths():
    locations = get_cache_locations()

    assert all(isinstance(location, Path) for location in locations)


def test_get_temporary_locations():
    locations = get_temporary_locations()

    assert isinstance(locations, list)


def test_get_temporary_locations_returns_paths():
    locations = get_temporary_locations()

    assert all(isinstance(location, Path) for location in locations)


def test_get_category_from_temporary_location(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    file = temporary_location / "archivo.dat"
    file.write_text("Hello")

    temporary_locations = [temporary_location]

    assert get_category(
        file,
        temporary_locations=temporary_locations,
    ) == "temporary"


def test_is_temporary_location(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    file = temporary_location / "archivo.dat"
    file.write_text("Hello")

    assert is_temporary_location(
        file,
        [temporary_location],
    )


def test_is_not_temporary_location(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    normal_location = tmp_path / "documents"
    normal_location.mkdir()

    file = normal_location / "archivo.dat"
    file.write_text("Hello")

    assert not is_temporary_location(
        file,
        [temporary_location],
    )


def test_get_category_cache_location_has_priority(tmp_path):
    cache_location = tmp_path / "cache"
    cache_location.mkdir()

    file = cache_location / "archivo.tmp"
    file.write_text("Hello")

    assert get_category(
        file,
        cache_locations=[cache_location],
        temporary_locations=[cache_location],
    ) == "cache"


def test_get_category_unknown_file(tmp_path):
    file = tmp_path / "archivo.xyz"
    file.write_text("Hello")

    assert get_category(file) is None


def test_cleanup_folder_respects_all_rules(tmp_path):
    temporary_file = tmp_path / "cache.tmp"
    temporary_file.write_text("Hello")
    make_file_old(temporary_file)

    log_file = tmp_path / "server.log"
    log_file.write_text("Hello")

    protected_file = tmp_path / "important.tmp"
    protected_file.write_text("Hello")

    protected_location = tmp_path / "protected"
    protected_location.mkdir()

    protected_location_file = protected_location / "cache.tmp"
    protected_location_file.write_text("Hello")
    make_file_old(protected_location_file)

    result = cleanup_folder(
        tmp_path,
        protected=[protected_file],
        protected_locations=[protected_location],
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5

    assert not temporary_file.exists()
    assert log_file.exists()
    assert protected_file.exists()
    assert protected_location_file.exists()


def test_clean_files_counts_errors(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("Hello")

    with patch.object(Path, "unlink", side_effect=PermissionError):
        result = clean_files([file])

    assert result["deleted"] == 0
    assert result["freed"] == 0
    assert result["errors"] == 1


def test_cleanup_folder_counts_skipped_protected_file(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("Hello")

    result = cleanup_folder(
        tmp_path,
        protected=[file],
        selected_categories=["temporary"],
    )

    assert result["deleted"] == 0
    assert result["freed"] == 0
    assert result["skipped"] == 1


def test_should_clean_temporary_location(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    file = temporary_location / "archivo.dat"
    file.write_text("Hello")
    make_file_old(file)

    assert should_clean(
        file,
        ["temporary"],
        temporary_locations=[temporary_location],
    )


def test_is_cleanable_temporary_file():
    file = Path("archivo.dat")

    result = is_cleanable(
        file,
        category="temporary",
    )

    assert result is True


def test_cleanup_folder_uses_temporary_location(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    file = temporary_location / "archivo.dat"
    file.write_text("Hello")
    make_file_old(file)

    result = cleanup_folder(
        temporary_location,
        selected_categories=["temporary"],
        temporary_locations=[temporary_location],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert not file.exists()


def test_cleanup_folder_temporary_location_respects_protection(tmp_path):
    temporary_location = tmp_path / "temp"
    temporary_location.mkdir()

    clean_file = temporary_location / "archivo.dat"
    clean_file.write_text("Hello")
    make_file_old(clean_file)

    protected_file = temporary_location / "importante.dat"
    protected_file.write_text("Hello")
    make_file_old(protected_file)

    result = cleanup_folder(
        temporary_location,
        protected=[protected_file],
        selected_categories=["temporary"],
        temporary_locations=[temporary_location],
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert result["skipped"] == 1

    assert not clean_file.exists()
    assert protected_file.exists()


def test_is_old_enough(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("test")

    make_file_old(file)

    assert is_old_enough(file, min_age_hours=24) is True


def test_should_not_clean_recent_file(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("test")

    recent_time = datetime.now().timestamp() - (2 * 60 * 60)
    os.utime(file, (recent_time, recent_time))

    assert should_clean(
        file,
        selected_categories=["temporary"],
        temporary_locations=[tmp_path],
    ) is False


def test_should_clean_old_file(tmp_path):
    file = tmp_path / "archivo.tmp"
    file.write_text("test")

    make_file_old(file)

    assert should_clean(
        file,
        selected_categories=["temporary"],
        temporary_locations=[tmp_path],
    ) is True

def test_strict_categories_does_not_reject_cache_by_extension(tmp_path):
    cache_location = tmp_path / "cache"
    cache_location.mkdir()

    file = cache_location / "image.dat"
    file.write_text("Hello")
    make_file_old(file)

    result = cleanup_folder(
        cache_location,
        selected_categories=["cache"],
        cache_locations=[cache_location],
        strict_categories=True,
    )

    assert result["deleted"] == 1
    assert result["freed"] == 5
    assert not file.exists()