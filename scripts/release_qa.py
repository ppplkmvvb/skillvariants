"""Read-only, fail-closed verification of explicitly selected release artifacts."""
from __future__ import annotations

import argparse
import ast
import configparser
import hashlib
import json
import re
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
FORBIDDEN = {"fixtures", "evaluation", "evals", "research", ".cache", "__pycache__", ".skillvariants",
             ".git", ".env", ".venv", ".netrc", ".pypirc", ".ssh", ".aws",
             "credentials", "credentials.json", "secrets.json"}


def _unsafe(name: str) -> bool:
    path = PurePosixPath(name)
    return (path.is_absolute() or "\\" in name or ".." in path.parts or ":" in path.parts[0]
            or any(part.lower() in FORBIDDEN or part.lower().startswith(".env.") for part in path.parts))


def _version(raw: bytes) -> str | None:
    for node in ast.parse(raw.decode("utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def _read_archive(path: Path, kind: str) -> dict[str, bytes]:
    if kind == "wheel":
        with zipfile.ZipFile(path) as archive:
            names = [i.filename for i in archive.infolist() if not i.is_dir()]
            if len(names) != len(set(names)):
                raise ValueError("duplicate archive members")
            return {name: archive.read(name) for name in names}
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        if any(not (m.isfile() or m.isdir()) for m in members):
            raise ValueError("sdist contains links or special files")
        files = [m for m in members if m.isfile()]
        if len(files) != len({m.name for m in files}):
            raise ValueError("duplicate archive members")
        return {m.name: archive.extractfile(m).read() for m in files}


def check_distributions(wheel: Path, sdist: Path, expected_version: str) -> list[str]:
    errors = []
    for kind, path in (("wheel", wheel), ("sdist", sdist)):
        try:
            files = _read_archive(path, kind)
            for name, content in files.items():
                if _unsafe(name):
                    errors.append(f"{kind}: forbidden member {name}")
                if SECRET.search(content):
                    errors.append(f"{kind}: credential-like content in {name}")
            if kind == "sdist":
                roots = {PurePosixPath(n).parts[0] for n in files}
                if len(roots) != 1:
                    raise ValueError("sdist must have one root directory")
                files = {n.split("/", 1)[1]: content for n, content in files.items()}
                meta_name, init_name, cli_name = "PKG-INFO", "src/skillvariants/__init__.py", "src/skillvariants/cli.py"
                project = tomllib.loads(files["pyproject.toml"].decode("utf-8"))["project"]
                if project.get("name") != "skillvariants" or project.get("version") != expected_version:
                    errors.append("sdist: pyproject name/version mismatch")
            else:
                metadata = [n for n in files if n.endswith(".dist-info/METADATA")]
                if len(metadata) != 1:
                    raise ValueError("wheel requires exactly one METADATA")
                meta_name, init_name, cli_name = metadata[0], "skillvariants/__init__.py", "skillvariants/cli.py"
                config = configparser.ConfigParser()
                config.read_string(files[meta_name.removesuffix("METADATA") + "entry_points.txt"].decode("utf-8"))
                if config.get("console_scripts", "skillvariants", fallback="") != "skillvariants.cli:app":
                    errors.append("wheel: missing skillvariants console entry point")
            meta = BytesParser().parsebytes(files[meta_name])
            if meta.get("Name") != "skillvariants" or meta.get("Version") != expected_version:
                errors.append(f"{kind}: metadata name/version mismatch (expected {expected_version})")
            if not meta.get("Requires-Python"):
                errors.append(f"{kind}: missing Requires-Python")
            if _version(files[init_name]) != expected_version:
                errors.append(f"{kind}: package __version__ mismatch")
            if not files[cli_name].strip():
                errors.append(f"{kind}: CLI module missing or empty")
        except (OSError, ValueError, KeyError, IndexError, SyntaxError, configparser.Error,
                tarfile.TarError, zipfile.BadZipFile) as exc:
            errors.append(f"{kind}: cannot verify {path.name}: {exc}")
    return errors


def check_skill_archive(skill_dir: Path, archive_path: Path) -> list[str]:
    try:
        if not (skill_dir / "SKILL.md").read_text("utf-8").strip():
            return ["Skill SKILL.md is empty"]
        expected = {}
        for path in sorted(skill_dir.rglob("*")):
            if path.is_symlink():
                return [f"Skill tree contains symlink: {path.name}"]
            if path.is_file():
                name = f"{skill_dir.name}/{path.relative_to(skill_dir).as_posix()}"
                if _unsafe(name) or SECRET.search(path.read_bytes()):
                    return [f"Skill tree contains forbidden file/content: {name}"]
                if path.suffix == ".md":
                    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text("utf-8")):
                        target = urlsplit(link.strip("<>"))
                        if target.scheme or target.netloc or not target.path:
                            continue
                        referenced = (path.parent / unquote(target.path)).resolve()
                        if not referenced.is_relative_to(skill_dir.resolve()) or not referenced.is_file():
                            return [f"Skill reference missing or outside deliverable: {name} -> {link}"]
                expected[name] = path.read_bytes()
        with zipfile.ZipFile(archive_path) as archive:
            actual = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
        if actual != expected:
            return ["Skill archive does not exactly match skills/skillvariants"]
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return [f"Cannot verify separate Skill archive: {exc}"]
    return []


def check_fixture_provenance(root: Path) -> list[str]:
    errors = []
    try:
        fixtures_dir = root / "tests/fixtures"
        data = json.loads((fixtures_dir / "SOURCES.json").read_text("utf-8"))
        records = data["fixtures"]
        expected = {p.relative_to(fixtures_dir).as_posix() for p in fixtures_dir.rglob("*.md")}
        declared = [r["path"] for r in records]
        if set(declared) != expected or len(declared) != len(set(declared)):
            errors.append("Fixture provenance does not cover exactly every Markdown fixture")
        licenses = {r["path"]: r for r in data["upstream_licenses"]}
        for record in records:
            path = (fixtures_dir / record["path"]).resolve()
            if not path.is_relative_to(fixtures_dir.resolve()):
                errors.append("Fixture provenance path escapes fixture directory")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                errors.append(f"Fixture hash mismatch: {record['path']}")
            if not record.get("license"):
                errors.append(f"Fixture license missing: {record['path']}")
            for name in record.get("license_files", []):
                if name not in licenses:
                    errors.append(f"Fixture references undeclared license: {name}")
        for name, record in licenses.items():
            path = (root / name).resolve()
            if not path.is_relative_to((fixtures_dir / "licenses").resolve()):
                errors.append(f"License path outside fixture licenses: {name}")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                errors.append(f"License hash mismatch: {name}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"Cannot verify fixture provenance: {exc}")
    return errors


def verify_release(root: Path, wheel: Path, sdist: Path, skill_archive: Path) -> list[str]:
    project = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]
    errors = check_distributions(wheel, sdist, project["version"])
    errors.extend(check_skill_archive(root / "skills/skillvariants", skill_archive))
    errors.extend(check_fixture_provenance(root))
    for path in (root / "web").rglob("*"):
        if path.is_file() and (_unsafe(path.relative_to(root / "web").as_posix()) or SECRET.search(path.read_bytes())):
            errors.append(f"Web bundle contains forbidden file/content: {path.name}")
    result = subprocess.run([sys.executable, "-B", str(root / "scripts/export_web_data.py"), "--check"],
                            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if result.returncode:
        errors.append("Web export is stale, missing, or invalid: " + (result.stderr or result.stdout).strip()[:1000])
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    parser.add_argument("--skill-archive", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        errors = verify_release(args.root.resolve(), args.wheel.resolve(), args.sdist.resolve(), args.skill_archive.resolve())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        errors = [f"Release verification failed: {exc}"]
    print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
