"""Fail-closed checks for actual release deliverables."""
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_gate():
    spec = importlib.util.spec_from_file_location("release_qa_test", ROOT / "scripts/release_qa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archives(tmp_path, version="0.3.0", extra=None):
    metadata = f"Metadata-Version: 2.4\nName: skillvariants\nVersion: {version}\nRequires-Python: >=3.11\n"
    wheel = tmp_path / f"skillvariants-{version}-py3-none-any.whl"
    files = {"skillvariants/__init__.py": f'__version__ = "{version}"\n',
             "skillvariants/cli.py": "app = None\n",
             f"skillvariants-{version}.dist-info/METADATA": metadata,
             f"skillvariants-{version}.dist-info/entry_points.txt": "[console_scripts]\nskillvariants = skillvariants.cli:app\n"}
    files.update(extra or {})
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    sdist = tmp_path / f"skillvariants-{version}.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name, content in {"PKG-INFO": metadata, "pyproject.toml": f'[project]\nname="skillvariants"\nversion="{version}"\n',
                              "src/skillvariants/__init__.py": f'__version__ = "{version}"\n',
                              "src/skillvariants/cli.py": "app = None\n"}.items():
            raw = content.encode()
            item = tarfile.TarInfo(f"skillvariants-{version}/{name}")
            item.size = len(raw)
            archive.addfile(item, io.BytesIO(raw))
    return wheel, sdist


def test_import_is_side_effect_free(tmp_path):
    code = "import runpy; runpy.run_path(" + repr(str(ROOT / "scripts/release_qa.py")) + ")"
    result = subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout == b""
    assert list(tmp_path.iterdir()) == []


def test_missing_wheel_and_sdist_fail(tmp_path):
    gate = load_gate()
    errors = gate.check_distributions(tmp_path / "missing.whl", tmp_path / "missing.tar.gz", "0.3.0")
    assert len(errors) >= 2
    assert any("wheel" in e.lower() for e in errors)
    assert any("sdist" in e.lower() for e in errors)


def test_actual_metadata_accepts_current_version(tmp_path):
    wheel, sdist = archives(tmp_path)
    assert load_gate().check_distributions(wheel, sdist, "0.3.0") == []


def test_metadata_version_mismatch_fails(tmp_path):
    wheel, sdist = archives(tmp_path, "0.2.0")
    assert load_gate().check_distributions(wheel, sdist, "0.3.0")


def test_malformed_entrypoints_returns_failed_check(tmp_path):
    wheel, sdist = archives(tmp_path, extra={"skillvariants-0.3.0.dist-info/entry_points.txt": "invalid"})
    assert load_gate().check_distributions(wheel, sdist, "0.3.0")


@pytest.mark.parametrize("path", ["tests/fixtures/sample.md", ".cache/token", "evaluation/results.json", "evals/run.json",
                                  ".skillvariants/studies/id/manifest.json", ".env", "secrets.json", "../escape.py"])
def test_forbidden_distribution_content_fails(tmp_path, path):
    wheel, sdist = archives(tmp_path, extra={path: "private"})
    errors = load_gate().check_distributions(wheel, sdist, "0.3.0")
    assert errors and any(path in e for e in errors)


def test_embedded_github_credential_fails(tmp_path):
    wheel, sdist = archives(tmp_path, extra={"skillvariants/private.py": 'TOKEN = "ghp_' + "x" * 36 + '"'})
    assert load_gate().check_distributions(wheel, sdist, "0.3.0")


def test_skill_archive_must_exactly_match_separately_installed_tree(tmp_path):
    skill = tmp_path / "skillvariants"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: skillvariants\n---\nRead the sources.\n", encoding="utf-8")
    artifact = tmp_path / "skill.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.write(skill / "SKILL.md", "skillvariants/SKILL.md")
    assert load_gate().check_skill_archive(skill, artifact) == []
    (skill / "SKILL.md").write_text("changed", encoding="utf-8")
    assert load_gate().check_skill_archive(skill, artifact)


def test_skill_archive_rejects_missing_local_reference(tmp_path):
    skill = tmp_path / "skillvariants"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: skillvariants\n---\nRead [rules](references/missing.md).\n", encoding="utf-8")
    artifact = tmp_path / "skill.zip"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.write(skill / "SKILL.md", "skillvariants/SKILL.md")
    assert load_gate().check_skill_archive(skill, artifact)


def test_release_cli_requires_explicit_distributions():
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/release_qa.py")],
                            capture_output=True, timeout=30)
    assert result.returncode != 0
    assert b"--wheel" in result.stderr and b"--sdist" in result.stderr


def test_smoke_rejects_source_pythonpath(tmp_path):
    import os
    result = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/package_smoke.py")],
                            cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                            capture_output=True, timeout=30)
    assert result.returncode != 0
    assert b"PYTHONPATH" in result.stderr


def test_provenance_hashes_and_complete_fixture_inventory(tmp_path):
    import hashlib
    fixtures = tmp_path / "tests/fixtures"
    fixtures.mkdir(parents=True)
    path = fixtures / "sample.md"
    path.write_bytes(b"sample\n")
    data = {"fixtures": [{"path": "sample.md", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "license": "Apache-2.0", "license_files": []}], "upstream_licenses": []}
    (fixtures / "SOURCES.json").write_text(json.dumps(data))
    gate = load_gate()
    assert gate.check_fixture_provenance(tmp_path) == []
    path.write_bytes(b"changed\n")
    assert any("hash mismatch" in error for error in gate.check_fixture_provenance(tmp_path))
    path.write_bytes(b"sample\n")
    (fixtures / "undeclared.md").write_text("unlicensed")
    assert any("exactly every" in error for error in gate.check_fixture_provenance(tmp_path))
