from pathlib import Path
import os
from app.config import CATEGORIES


def get_files(folder: Path) -> list[Path]:
    """Return a list of files from a directory."""

    if not folder.exists():
        raise FileNotFoundError(f"The path doesn't exist: {folder}")

    if not folder.is_dir():
        raise NotADirectoryError("The path isn't a directory.")
    
    files = []

    for item in folder.rglob("*"):
        if item.is_file():
            files.append(item)

    return files


def get_files_size(files: list[Path]) -> int:
    """Return total size of files"""
    total = 0

    for item in files:
        try:
            total += item.stat().st_size
        except (PermissionError, FileNotFoundError):
            continue

    return total

def get_cleanup_info(folder:Path) -> dict:
    """Return information about files in a directory."""

    files = get_files(folder)
    size = get_files_size(files)

    return {
        "files": len(files),
        "size": size
    }

def get_category(
        file: Path,
        cache_locations: list[Path] | None = None,
        temporary_locations: list[Path] | None = None
) -> str | None:
    """Return the category of a file."""

    if cache_locations is None:
        cache_locations = []

    if temporary_locations is None:
        temporary_locations = []

    if is_cache_location(file, cache_locations):
        return "cache"

    if is_temporary_location(file, temporary_locations):
        return "temporary"
    
    suffix = file.suffix.lower()

    for category, extensions in CATEGORIES.items():
        if suffix in extensions:
            return category

    return None

def is_cache_location(
        file: Path,
        cache_locations: list[Path]
) -> bool:
    """Return True if the file is inside a known cache location."""

    for location in cache_locations:
        if file.is_relative_to(location):
            return True

    return False

def get_cache_locations() -> list[Path]:
    """Return known cache locations for the current user."""
    return []

def get_temporary_locations() -> list[Path]:
    """Return known temporary locations for the current user."""

    locations = []

    temp_directory = os.getenv("TEMP")

    if temp_directory:
        locations.append(Path(temp_directory))

    return locations

def is_temporary_location(
        file: Path,
        temporary_locations: list[Path]
) -> bool:
    """Return True if the file is inside a known temporary location."""

    for location in temporary_locations:
        if file.is_relative_to(location):
            return True

    return False

def get_log_locations() -> list[Path]:
    """Return known log locations for the current user."""

    locations = []

    local_app_data = os.getenv("LOCALAPPDATA")

    if local_app_data:
        locations.append(
            Path(local_app_data) / "Logs"
        )

    return locations

def get_system_locations() -> dict[str, list[Path]]:
    """Return known cleanup locations grouped by category."""

    return {
        "temporary": get_temporary_locations(),
        "cache": get_cache_locations(),
        "logs": get_log_locations(),
    }