"""
Regression check for the public build (audit HTML-2).

Copies the tracked files of this repository into a temporary directory with
no HALLUX checkout beside it, then asserts:

1. the build succeeds and leaves no {{HALLUX_*}} token in docs/, using
   dev/hallux-snapshot.json;
2. with BLVKWARE_REQUIRE_HALLUX=1 the build aborts, and the aborted run
   leaves docs/ byte for byte as it was (the publish is atomic).

Usage: python3 dev/check-public-build.py
"""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tree_hash(path):
    digest = hashlib.sha256()
    for dirpath, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(dirpath, name)
            digest.update(os.path.relpath(full, path).encode())
            with open(full, "rb") as fh:
                digest.update(hashlib.sha256(fh.read()).digest())
    return digest.hexdigest()


def check_failed_publication(repo):
    spec = importlib.util.spec_from_file_location("site_build", Path(repo, "dev/build-static.py"))
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    output = Path(repo, "docs")
    (output / "assets/site-shell.css").write_text("previous release")
    before = tree_hash(output)
    publish = builder.publish
    rename = os.rename

    def fail_after_publish(*args):
        publish(*args)
        raise OSError("injected failure")

    def fail_install(src, dst):
        if Path(src).name.startswith(".docs-staging-") and Path(dst) == output:
            raise OSError("injected failure")
        rename(src, dst)

    for catalog_only in (False, True):
        for target, attr, failure in ((builder, "publish", fail_after_publish),
                                      (os, "rename", fail_install)):
            with patch.object(target, attr, failure):
                try:
                    builder.main(catalog_only=catalog_only)
                except OSError as exc:
                    if str(exc) != "injected failure":
                        raise
                else:
                    raise AssertionError("build did not reach injected failure")
            assert output.is_dir() and tree_hash(output) == before
            assert not list(Path(repo).glob(".docs-staging-*"))
            assert not Path(repo, "docs.previous").exists()


def main():
    files = subprocess.run(["git", "-C", ROOT, "ls-files", "-co", "--exclude-standard", "-z"],
                           check=True, capture_output=True).stdout.decode().split("\0")
    work = tempfile.mkdtemp(prefix="public-build-")
    repo = os.path.join(work, "site-repo")  # no ../hallux beside it
    try:
        for rel in filter(None, files):
            src = os.path.join(ROOT, rel)
            if not os.path.isfile(src):
                continue
            dst = os.path.join(repo, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        env = {k: v for k, v in os.environ.items() if k not in ("HALLUX_PATH", "BLVKWARE_REQUIRE_HALLUX")}
        build = [sys.executable, os.path.join("dev", "build-static.py")]

        run = subprocess.run(build, cwd=repo, env=env, capture_output=True, text=True)
        if run.returncode != 0:
            print(run.stdout[-3000:], run.stderr[-3000:])
            print("FAIL: public build without HALLUX exited %d" % run.returncode)
            return 1
        leftovers = set()
        for dirpath, _dirs, names in os.walk(os.path.join(repo, "docs")):
            for name in names:
                if name.endswith((".html", ".txt", ".json", ".xml")):
                    with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as fh:
                        leftovers.update(re.findall(r"\{\{HALLUX_[A-Z0-9_]+\}\}", fh.read()))
        if leftovers:
            print("FAIL: unresolved tokens in docs/: %s" % ", ".join(sorted(leftovers)))
            return 1
        print("ok: public build succeeded with no unresolved HALLUX tokens")

        before = tree_hash(os.path.join(repo, "docs"))
        strict = dict(env, BLVKWARE_REQUIRE_HALLUX="1")
        run = subprocess.run(build, cwd=repo, env=strict, capture_output=True, text=True)
        if run.returncode == 0:
            print("FAIL: BLVKWARE_REQUIRE_HALLUX=1 should abort without HALLUX")
            return 1
        if tree_hash(os.path.join(repo, "docs")) != before:
            print("FAIL: an aborted build changed docs/")
            return 1
        if any(n.startswith(".docs-staging-") for n in os.listdir(repo)):
            print("FAIL: staging directory left behind")
            return 1
        with patch.dict(os.environ, env, clear=True):
            check_failed_publication(repo)
        print("ok: strict preflight, late abort and failed installation preserve docs/")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
