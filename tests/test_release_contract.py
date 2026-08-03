from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIRS = ("memory_data/", "knowledge_base/", "data_science_kb/")
LF_PATTERNS = ("*.py", "*.md", "*.toml", "*.yml", "*.yaml", "*.json", "*.sh")
SDIST_EXCLUDES = {"/.vscode", "/AGENTS.md", "/my_main.py", "/todo.md"}
REQUIRED_FILES = (
    ".gitattributes",
    "README.md",
    "README.en.md",
    "docs/guide.zh-CN.md",
    "docs/guide.en.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "AGENTS.md",
    ".github/workflows/ci.yml",
)


def load_pyproject() -> dict:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def test_version_and_release_metadata_are_consistent() -> None:
    project = load_pyproject()["project"]
    init_text = (ROOT / "lingye_agent" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init_text, re.MULTILINE)

    assert match is not None
    assert project["version"] == match.group(1) == "0.1.0"
    assert project["readme"] == "README.en.md"
    assert "Development Status :: 4 - Beta" in project["classifiers"]

    urls = project["urls"]
    assert urls["Homepage"] == "https://github.com/Ling-ye/Lingye_Agent"
    assert urls["Repository"] == "https://github.com/Ling-ye/Lingye_Agent"
    assert urls["Issues"].endswith("/issues")
    assert urls["Changelog"].endswith("/CHANGELOG.md")
    assert urls["Documentation"].endswith("/docs/guide.en.md")
    assert all("yourname" not in value.lower() for value in urls.values())


def test_required_release_files_exist() -> None:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    assert not missing, f"missing release files: {missing}"


def test_repository_text_and_sdist_policies_are_explicit() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in LF_PATTERNS:
        assert f"{pattern} text eol=lf" in attributes

    sdist = load_pyproject()["tool"]["hatch"]["build"]["targets"]["sdist"]
    assert set(sdist["exclude"]) == SDIST_EXCLUDES


def test_public_docs_contain_no_repository_placeholders_or_pypi_claim() -> None:
    docs = [
        ROOT / "README.md",
        ROOT / "README.en.md",
        ROOT / "docs" / "guide.zh-CN.md",
        ROOT / "docs" / "guide.en.md",
    ]
    forbidden = ("<your-repo-url>", "github.com/yourname", "pypi.org/project/lingye-agent")

    for path in docs:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert all(token not in lowered for token in forbidden), path
        assert re.search(r"pip install\s+lingye-agent(?:\s|$)", text) is None, path


def iter_relative_markdown_links(path: Path):
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean_target = target.split("#", 1)[0]
        if clean_target:
            yield clean_target


def test_relative_documentation_links_resolve() -> None:
    docs = (
        ROOT / "README.md",
        ROOT / "README.en.md",
        ROOT / "docs" / "guide.zh-CN.md",
        ROOT / "docs" / "guide.en.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
    )
    broken = []
    for path in docs:
        for target in iter_relative_markdown_links(path):
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    assert not broken, f"broken relative links: {broken}"


def test_runtime_data_is_ignored_and_not_tracked() -> None:
    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for directory in RUNTIME_DIRS:
        assert f"/{directory}" in ignore_text

    git = shutil.which("git")
    assert git is not None, "git is required for the release contract check"
    result = subprocess.run(
        [git, "ls-files", "--", *[item.rstrip("/") for item in RUNTIME_DIRS]],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line for line in result.stdout.splitlines() if line]
    tracked_and_present = [path for path in tracked if (ROOT / path).exists()]
    assert not tracked_and_present, (
        f"runtime data is tracked and present: {tracked_and_present}"
    )
