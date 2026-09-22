from pathlib import Path

OUTPUT_FILE = "project_dump.txt"

INCLUDED_EXTENSIONS = {
    ".py",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "build",
    "dist",
    ".qt_for_python",  # si présent
}

EXCLUDED_FILES = {
    "project_dump.txt",
}

with open(OUTPUT_FILE, "w", encoding="utf-8") as out:

    for file in sorted(Path(".").rglob("*")):

        if not file.is_file():
            continue

        # Exclure certains répertoires
        if any(part in EXCLUDED_DIRS for part in file.parts):
            continue

        # Exclure certains fichiers
        if file.name in EXCLUDED_FILES:
            continue

        # Garder seulement certaines extensions
        if file.suffix.lower() not in INCLUDED_EXTENSIONS:
            continue

        out.write("\n")
        out.write("=" * 100)
        out.write("\n")
        out.write(f"FILE : {file.as_posix()}")
        out.write("\n")
        out.write("=" * 100)
        out.write("\n\n")

        try:
            out.write(file.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            out.write(file.read_text(encoding="utf-8", errors="ignore"))

        out.write("\n\n")