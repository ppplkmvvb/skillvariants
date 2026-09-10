"""Exercise deployment mechanics through an in-memory API; never publish."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location("deploy_test", ROOT / "scripts/deploy_gh_pages.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fake_api(deployer, calls, status=200, patch_status=200):
    def call(endpoint, method="GET", body=None):
        calls.append((endpoint, method, body))
        if method == "GET":
            if status != 200:
                raise deployer.ApiError(status, "branch lookup failed")
            return {"object": {"sha": "old-pages"}}
        if method == "PATCH" and patch_status != 200:
            raise deployer.ApiError(patch_status, "update failed")
        return {"sha": "new-" + endpoint.split("/")[-1]}
    return call


@pytest.mark.parametrize("existing", [True, False])
def test_pages_tree_contains_only_web_and_correct_ref_operation(tmp_path, existing):
    deployer = module()
    (tmp_path / "index.html").write_text("hello", encoding="utf-8")
    calls = []
    deployer.deploy(tmp_path, fake_api(deployer, calls, status=200 if existing else 404))
    tree = next(body for endpoint, method, body in calls if endpoint == "git/trees")
    assert "base_tree" not in tree
    assert [entry["path"] for entry in tree["tree"]] == ["index.html"]
    commit = next(body for endpoint, method, body in calls if endpoint == "git/commits")
    assert commit["parents"] == (["old-pages"] if existing else [])
    refs = [(endpoint, method, body) for endpoint, method, body in calls if method in ("PATCH", "POST") and endpoint.startswith("git/refs")]
    assert len(refs) == 1
    assert refs[0][1] == ("PATCH" if existing else "POST")
    if existing:
        assert refs[0][0] == "git/refs/heads/gh-pages"
        assert refs[0][2]["force"] is False


@pytest.mark.parametrize("status", [401, 403, 429, 500])
def test_non_404_lookup_failure_performs_no_mutations(tmp_path, status):
    deployer = module()
    (tmp_path / "index.html").write_text("hello")
    calls = []
    with pytest.raises(deployer.ApiError):
        deployer.deploy(tmp_path, fake_api(deployer, calls, status=status))
    assert all(method == "GET" for _, method, _ in calls)


def test_failed_patch_never_falls_back_to_create(tmp_path):
    deployer = module()
    (tmp_path / "index.html").write_text("hello")
    calls = []
    with pytest.raises(deployer.ApiError):
        deployer.deploy(tmp_path, fake_api(deployer, calls, patch_status=403))
    assert not any(endpoint == "git/refs" and method == "POST" for endpoint, method, _ in calls)
