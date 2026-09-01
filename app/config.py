import tempfile
from pathlib import Path

def get_temp_directory() -> Path:
    """Return the system temporary directory"""

    temp = Path(tempfile.gettempdir())

    return temp

def format_size(size:int) -> str:
    """Format size in a human-readable format."""

    if size < 1024:
        return f"{size} B"

    elif size < 1024 ** 2:
        valor = size / 1024
        return f"{valor:.2f} KB"

    elif size < 1024 ** 3:
        valor = size / (1024 ** 2)
        return f"{valor:.2f} MB"

    else:
        valor = size / (1024 ** 3)
        return f"{valor:.2f} GB"


MIN_FILE_AGE_HOURS = 24

CATEGORIES = {
    "temporary": [".tmp", ".temp"],
    "cache" : [".cache"],
    "logs": [".log"],
}

MIN_FILE_AGE_HOURS = 24