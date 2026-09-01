from app.scanner import get_files, get_files_size, get_cleanup_info

import pytest

def test_get_files(tmp_path):
    archive1 = tmp_path / "archivo1.txt"
    archive1.write_text("Hello")

    archive2 = tmp_path / "archivo2.txt"
    archive2.write_text("Hello")

    archive3 = tmp_path / "archivo3.txt"
    archive3.write_text("Hello")

    files = get_files(tmp_path)

    assert len(files) == 3

def test_get_files_size(tmp_path):
    archive1 = tmp_path / "archivo1.txt"
    archive1.write_text("Hello")

    archive2 = tmp_path / "archivo2.txt"
    archive2.write_text("Hello")

    archive3 = tmp_path / "archivo3.txt"
    archive3.write_text("Hello")

    files = get_files(tmp_path)

    size = get_files_size(files)

    assert len(files) == 3
    assert size == 15

def test_get_cleanup_info(tmp_path):
    archive1 = tmp_path / "archivo1.txt"
    archive1.write_text("Hello")

    archive2 = tmp_path / "archivo2.txt"
    archive2.write_text("Hello")

    archive3 = tmp_path / "archivo3.txt"
    archive3.write_text("Hello")

    info = get_cleanup_info(tmp_path)

    assert info["files"] == 3
    assert info["size"] == 15

def test_get_files_directory_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_files(tmp_path / "no existe")

def test_get_files_path_is_file(tmp_path):
    archive1 = tmp_path / "archivo2.txt"
    archive1.write_text("Hello")

    with pytest.raises(NotADirectoryError):
        get_files(archive1)

def test_get_files_recursive(tmp_path):
    archive_principal = tmp_path / "archivo_principal.txt"
    archive_principal.write_text("Hello")

    subfolder = tmp_path / "cache"
    subfolder.mkdir()

    archive1 = subfolder / "archivo1.txt"
    archive1.write_text("Hello")

    archive2 = subfolder / "archivo2.txt"
    archive2.write_text("Hello")

    files = get_files(tmp_path)

    assert len(files) == 3