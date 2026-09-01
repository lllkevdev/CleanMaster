from pathlib import Path

import time
import ctypes

from app.scanner import get_files, get_category

from app.config import CATEGORIES, MIN_FILE_AGE_HOURS

def clean_files(files: list[Path]) -> dict:
    """Delete the given files and return cleanup statistics."""

    deleted = 0
    freed = 0
    errors = 0

    for item in files:
        try:
            size = item.stat().st_size
            item.unlink()

            deleted += 1
            freed += size
        except PermissionError:
            errors += 1
            continue

        except FileNotFoundError:
            continue

    return {
        "deleted": deleted,
        "freed": freed,
        "errors": errors
    }

def is_protected(file: Path, protected: list[Path]) -> bool:
    """Return True if a file is protected."""
    return file in protected

def is_cleanable(
    file: Path,
    category: str | None = None
) -> bool:
    """Return True if a file can be cleaned."""

    if category in ("temporary", "cache", "logs"):
        return True

    return file.suffix.lower() == ".tmp"

def cleanup_folder(
    folder: Path,
    protected: list[Path] | None = None,
    protected_locations: list[Path] | None = None,
    selected_categories: list[str] | None = None,
    cache_locations: list[Path] | None = None,
    temporary_locations: list[Path] | None = None,
    strict_categories: bool = False,
) -> dict:
    """Clean a folder according to the cleanup rules."""

    if protected is None:
        protected = []

    if protected_locations is None:
        protected_locations = []

    if selected_categories is None:
        selected_categories = list(CATEGORIES.keys())

    if cache_locations is None:
        cache_locations = []

    if temporary_locations is None:
        temporary_locations = []

    files = get_files(folder)

    cleanable_files = []
    skipped = 0

    for file in files:
        if is_protected(file, protected):
            skipped += 1
            continue

        if is_protected_location(file, protected_locations):
            skipped += 1
            continue

        if should_clean(
            file,
            selected_categories,
            cache_locations=cache_locations,
            temporary_locations=temporary_locations,
        ):
            category = get_category(
                file,
                cache_locations=cache_locations,
                temporary_locations=temporary_locations,
            )

            if (
                strict_categories
                and category in ("temporary", "logs")
                and file.suffix.lower() not in CATEGORIES[category]
            ):
                skipped += 1
                continue

            cleanable_files.append(file)

        else:
            skipped += 1

    result = clean_files(cleanable_files)

    result["skipped"] = skipped

    return result

def is_protected_location(file: Path, protected_locations: list[Path]) -> bool:
    """Return True if a file is inside of protected location."""

    for location in protected_locations:
        if file.is_relative_to(location):
            return True

    return False

def is_category_selected(
        category: str | None,
        selected_categories: list[str]
) -> bool:
    """Return True if a category was selected by the user."""

    return category in selected_categories

def should_clean(
    file: Path,
    selected_categories: list[str],
    cache_locations: list[Path] | None = None,
    temporary_locations: list[Path] | None = None
) -> bool:
    """Return True if the file belongs to a selected category and is safe to clean."""

    if cache_locations is None:
        cache_locations = []

    if temporary_locations is None:
        temporary_locations = []

    if selected_categories is None:
        selected_categories = list(CATEGORIES.keys())

    category = get_category(
        file,
        cache_locations=cache_locations,
        temporary_locations=temporary_locations
    )

    if not is_cleanable(file, category):
        return False

    if not is_category_selected(category, selected_categories):
        return False

    if not is_old_enough(file):
        return False

    return True

def empty_recycle_bin() -> dict:
    """Empty the Windows Recycle Bin."""

    try:
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(
            None,
            None,
            0x00000007,
        )

        return {
            "success": result == 0
        }

    except OSError:
        return {
            "success": False
        }

def is_old_enough(
    file: Path,
    min_age_hours: int = MIN_FILE_AGE_HOURS,
) -> bool:
    """Return True if a file has not been modified recently."""

    try:
        modified_time = file.stat().st_mtime
    except (PermissionError, FileNotFoundError):
        return False

    age_seconds = time.time() - modified_time
    min_age_seconds = min_age_hours * 60 * 60

    return age_seconds >= min_age_seconds