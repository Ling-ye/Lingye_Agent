from __future__ import annotations

import argparse
import email
import sys
import zipfile
from pathlib import Path


def verify_wheel(path: Path) -> None:
    if not path.is_file() or path.suffix != ".whl":
        raise SystemExit(f"not a wheel: {path}")

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_name = next(
            (name for name in names if name.endswith(".dist-info/METADATA")),
            None,
        )
        if metadata_name is None:
            raise SystemExit("wheel has no METADATA")

        unexpected = [
            name
            for name in names
            if "__pycache__" in name
            or name.endswith((".pyc", ".db", ".sqlite", ".sqlite3"))
            or name.startswith(("tests/", "memory_data/", "knowledge_base/"))
        ]
        if unexpected:
            raise SystemExit(f"unexpected wheel entries: {unexpected}")

        metadata = email.message_from_bytes(archive.read(metadata_name))
        if metadata.get("Name") != "lingye-agent":
            raise SystemExit(f"unexpected package name: {metadata.get('Name')}")
        if metadata.get("Version") != "0.1.0":
            raise SystemExit(f"unexpected version: {metadata.get('Version')}")

        project_urls = metadata.get_all("Project-URL", [])
        if not project_urls or any("yourname" in value.lower() for value in project_urls):
            raise SystemExit(f"invalid project URLs: {project_urls}")

    print(f"verified {path.name}: {len(names)} entries")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the Lingye Agent release wheel")
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify_wheel(args.wheel.resolve())


if __name__ == "__main__":
    main()
