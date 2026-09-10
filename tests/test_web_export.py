"""Published examples must be reproducible comparisons of original sources."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

from skillvariants.comparison import compare_documents
from skillvariants.parser import parse_skill_md

ROOT = Path(__file__).resolve().parents[1]


def exporter():
    spec = importlib.util.spec_from_file_location("web_exporter", ROOT / "scripts/export_web_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_export_uses_complete_production_comparisons():
    payload = exporter().build_examples(ROOT)
    assert payload["schema_version"] == "2"
    assert payload["provenance"]["kind"] == "original_illustrative_examples"
    assert {e["id"] for e in payload["examples"]} == {"added", "preserved", "reversed"}
    for example in payload["examples"]:
        docs = []
        for side in ("a", "b"):
            source = example["sources"][side]
            raw = (ROOT / source["path"]).read_bytes()
            assert source["raw_sha256"] == hashlib.sha256(raw).hexdigest()
            assert source["content"] == raw.decode("utf-8")
            doc = parse_skill_md(source["content"])
            doc.source_metadata = {"path": source["path"], "kind": "original_illustrative_example"}
            docs.append(doc)
        expected = compare_documents(*docs)
        assert example["comparison"] == expected
        assert not example["comparison"]["truncation"]["truncated"]
        assert example["observation"] and example["interpretation"]
        for citation in example["citations"]:
            hunk = next(h for h in expected["hunks"] if h["hunk_id"] == citation["hunk_id"])
            for side in ("a", "b"):
                assert set(citation[f"{side}_lines"]) <= {
                    line["line_number"] for line in hunk[side]["lines"]}
        assert "repository_count" not in example


def test_export_check_succeeds_for_current_committed_data():
    result = subprocess.run([sys.executable, "-B", "scripts/export_web_data.py", "--check"],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    actual = json.loads((ROOT / "web/data/examples.json").read_text(encoding="utf-8"))
    assert actual == exporter().build_examples(ROOT)


def test_export_check_rejects_stale_data(tmp_path):
    module = exporter()
    destination = tmp_path / "examples.json"
    destination.write_text('{"schema_version":"old"}', encoding="utf-8")
    assert module.check_export(ROOT, destination) is False
    assert destination.read_text() == '{"schema_version":"old"}'


def test_served_data_excludes_unvalidated_historical_claims():
    assert {p.name for p in (ROOT / "web/data").glob("*.json")} == {"examples.json"}
    app = (ROOT / "web/app.js").read_text(encoding="utf-8")
    assert "related_variant_count" not in app
    assert "accepted_motifs" not in app
    assert "text_diff_brief" not in app


def test_frontend_routes_and_evidence_views_render_real_export():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is optional; required for the static frontend smoke check")
    script = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const exported = JSON.parse(fs.readFileSync('web/data/examples.json', 'utf8'));
const app = {innerHTML: '', addEventListener() {}};
const context = vm.createContext({URL, console,
  document: {getElementById: () => app, title: ''},
  window: {location: {hash: '#/'}, addEventListener() {}, scrollTo() {}},
  fetch: async () => ({ok: true, json: async () => exported})});
vm.runInContext(fs.readFileSync('web/app.js', 'utf8'), context);
(async () => {
  await vm.runInContext('route()', context);
  assert.ok(app.innerHTML.includes('Original examples'));
  assert.ok(!/undefined|NaN/.test(app.innerHTML));
  for (const example of exported.examples) {
    context.window.location.hash = '#/example/' + example.id;
    await vm.runInContext('route()', context);
    assert.ok(app.innerHTML.includes(example.title));
    assert.ok(app.innerHTML.includes('All hunks included'));
    const full = vm.runInContext("view='sources'; evidence(activeExample)", context);
    assert.ok(full.includes('description: Original illustrative implementation workflow.'));
    const diff = vm.runInContext("view='diff'; evidence(activeExample)", context);
    const escaped = vm.runInContext('esc(activeExample.comparison.unified_diff)', context);
    assert.ok(diff.includes(escaped));
  }
  for (const route of ['#/example/missing', '#/motif/old/0', '#/%E0%A4%A']) {
    context.window.location.hash = route;
    await vm.runInContext('route()', context);
    assert.ok(/not found|not available/.test(app.innerHTML));
    assert.ok(!/undefined|NaN/.test(app.innerHTML));
  }
  context.invalid = JSON.parse(JSON.stringify(exported));
  context.invalid.examples[0].citations[0].a_lines = [];
  assert.throws(() => vm.runInContext('validateData(invalid)', context), /citation/i);
  console.log('Routes, complete source/diff views, missing pages, and citation validation passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});
"""
    result = subprocess.run([node, "-"], input=script, cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
