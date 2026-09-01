# Clean Master 🧹

Clean Master is a Windows system-cleaning application built with Python and PySide6.

The project focuses on safe and controlled cleanup of temporary files, cache and logs, while minimizing the risk of deleting files that are still in use or were recently created.

## Features

* Automatic scan of known system cleanup locations.
* Detection of temporary files, cache and logs.
* Safe cleanup rules based on file age and protected locations.
* Files modified less than 24 hours ago are not considered candidates for cleanup.
* Cleanup operates only on files detected during the previous analysis.
* Protected files and protected locations are skipped.
* Detailed cleanup statistics: deleted files, freed space, skipped files and errors.
* Windows Recycle Bin management as a separate operation.
* PySide6 graphical interface.
* Automated test suite with pytest.

## Safety model

Clean Master follows a conservative cleanup policy.

A file can be deleted only when it:

1. Belongs to a known cleanup category.
2. Is included in the user's selected categories.
3. Is not explicitly protected.
4. Is not inside a protected location.
5. Has not been modified during the last 24 hours.
6. Was present in the analysis snapshot.
7. Still exists and is a regular file.
8. Still belongs to an allowed cleanup location immediately before deletion.

Files that do not satisfy these conditions are skipped.

## Technologies

* Python 3.12
* PySide6
* pytest
* pathlib
* Windows APIs via `ctypes`

## Project structure

```text
CleanMaster/
│
├── app/
│   ├── gui/
│   │   ├── __init__.py
│   │   └── main_window.py
│   │
│   ├── __init__.py
│   ├── cleaner.py
│   ├── config.py
│   ├── scanner.py
│   └── service.py
│
├── tests/
│   ├── test_cleaner.py
│   ├── test_scanner.py
│   └── test_service.py
│
├── .gitignore
├── main.py
└── requirements-dev.txt
```

## Installation

Clone the repository:

```bash
git clone https://github.com/lllkevdev/CleanMaster.git
cd CleanMaster
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements-dev.txt
```

## Run the application

```powershell
python main.py
```

## Run the tests

```powershell
python -m pytest
```

## Current status

Clean Master is currently in active development.

The backend includes automated safety rules and an extensive pytest suite. The PySide6 interface is being integrated with the completed backend.

## Future improvements

* More known cache locations.
* More advanced detection of files currently in use.
* Improved progress reporting.
* Application packaging for Windows.
* GitHub Actions for automated testing.
* Additional cleanup categories.

## License

This project is currently intended as a personal development and portfolio project.
