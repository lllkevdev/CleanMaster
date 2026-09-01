from pathlib import Path

from app.config import CATEGORIES
from app.scanner import (
    get_cleanup_info,
    get_category,
    get_files,
    get_system_locations,
)
from app.cleaner import (
    cleanup_folder,
    empty_recycle_bin as cleaner_empty_recycle_bin,
    is_protected,
    is_protected_location,
    is_old_enough,
)


def analyze_folder(folder: Path) -> dict:
    """Analyze a folder and return cleanup information."""
    return get_cleanup_info(folder)


def analyze_system() -> dict:
    """Analyze known system cleanup locations."""
    locations = get_system_locations()

    categories = {
        category: {
            "files": 0,
            "size": 0,
            "items": [],
        }
        for category in CATEGORIES
    }

    for category, category_locations in locations.items():
        for location in category_locations:
            if not location.exists() or not location.is_dir():
                continue

            files = get_files(location)

            for file in files:
                detected_category = get_category(
                    file,
                    cache_locations=locations["cache"],
                    temporary_locations=locations["temporary"],
                )

                if detected_category != category:
                    continue

                if category in CATEGORIES:
                    if (
                        category in ("temporary", "logs")
                        and file.suffix.lower()
                        not in CATEGORIES[category]
                    ):
                        continue

                if not is_old_enough(file):
                    continue

                try:
                    size = file.stat().st_size
                except (PermissionError, FileNotFoundError):
                    continue

                categories[category]["files"] += 1
                categories[category]["size"] += size
                categories[category]["items"].append(file)

    total_files = sum(
        data["files"]
        for data in categories.values()
    )

    total_size = sum(
        data["size"]
        for data in categories.values()
    )

    return {
        "categories": categories,
        "total": {
            "files": total_files,
            "size": total_size,
        },
    }


def clean_folder(
    folder: Path,
    protected: list[Path] | None = None,
    protected_locations: list[Path] | None = None,
    selected_categories: list[str] | None = None,
    cache_locations: list[Path] | None = None,
    temporary_locations: list[Path] | None = None,
) -> dict:
    """Clean a folder using the configured cleanup rules."""
    return cleanup_folder(
        folder,
        protected=protected,
        protected_locations=protected_locations,
        selected_categories=selected_categories,
        cache_locations=cache_locations,
        temporary_locations=temporary_locations,
    )


def clean_system(
    analysis_result: dict,
    selected_categories: list[str] | None = None,
    protected: list[Path] | None = None,
    protected_locations: list[Path] | None = None,
) -> dict:
    """Clean exactly the files returned by a previous system analysis."""

    if selected_categories is None:
        selected_categories = list(CATEGORIES.keys())

    if protected is None:
        protected = []

    if protected_locations is None:
        protected_locations = []

    locations = get_system_locations()

    result = {
        "deleted": 0,
        "freed": 0,
        "skipped": 0,
        "errors": 0,
    }

    for category in selected_categories:
        category_data = analysis_result["categories"].get(
            category,
            {},
        )

        files = category_data.get("items", [])

        for file in files:
            if is_protected(file, protected):
                result["skipped"] += 1
                continue

            if is_protected_location(
                file,
                protected_locations,
            ):
                result["skipped"] += 1
                continue

            if not file.exists():
                continue

            if not file.is_file():
                continue

            if not is_old_enough(file):
                result["skipped"] += 1
                continue

            allowed_locations = locations.get(category, [])

            if not any(
                file.is_relative_to(location)
                for location in allowed_locations
            ):
                result["skipped"] += 1
                continue

            detected_category = get_category(
                file,
                cache_locations=locations["cache"],
                temporary_locations=locations["temporary"],
            )

            if detected_category != category:
                result["skipped"] += 1
                continue

            if (
                category in ("temporary", "logs")
                and category in CATEGORIES
                and file.suffix.lower()
                not in CATEGORIES[category]
            ):
                result["skipped"] += 1
                continue

            try:
                size = file.stat().st_size
                file.unlink()

                result["deleted"] += 1
                result["freed"] += size

            except PermissionError:
                result["errors"] += 1

            except FileNotFoundError:
                continue

    return result


def empty_recycle_bin() -> dict:
    """Empty the Windows Recycle Bin."""
    return cleaner_empty_recycle_bin()
