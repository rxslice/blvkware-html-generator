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
        print("ok: aborted build left docs/ unchanged and cleaned up")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
