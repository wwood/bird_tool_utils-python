#!/usr/bin/env python3
"""
Prepare a release for a bird-suite Python package (setuptools_scm-versioned,
e.g. singlem, bird_tool_utils).

Mirrors the shape of bird_tool_utils' scripts/release_rust.py, adapted to how
these Python packages actually release:
  - version is NOT hand-edited in a TOML file; it's derived from the git tag
    and force-written into the package's version.py via setuptools_scm
  - CHANGELOG.md here has no "Unreleased" section convention (entries are
    added as e.g. "## v0.21.3" at release time), so this script confirms the
    changelog interactively rather than auto-moving an Unreleased block
  - release stops at commit+tag; GitHub Actions builds and publishes to PyPI
    after `git push --tags` (no local `twine`/`build` step here)

Run from the repository root, e.g.:
    python3 scripts/release_python.py --version 0.21.4
"""

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path


def run(cmd: list, *, check: bool = True) -> subprocess.CompletedProcess:
    printable = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"+ {printable}")
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=check)


def capture(cmd: list) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def validate_version(version: str) -> None:
    # PEP 440-ish: 1.2.3, 1.2.3a1, 1.2.3.post1, 1.2.3rc1 etc. Kept permissive
    # since setuptools_scm/pip accept a fair range of forms.
    if not re.fullmatch(r"\d+\.\d+\.\d+([A-Za-z0-9.+-]*)?", version):
        die(
            f"invalid version {version!r}; expected something like "
            "0.21.4, 0.21.4a1, or 0.21.4.post1"
        )


def check_clean_git() -> None:
    status = capture(["git", "status", "--porcelain"])
    if status:
        die("git working tree is not clean; commit or stash changes first")


def get_version_file(pyproject: Path) -> Path:
    if not pyproject.exists():
        die(f"{pyproject} not found - run this from the package repo root")
    data = tomllib.loads(pyproject.read_text())
    scm = data.get("tool", {}).get("setuptools_scm")
    if scm is None:
        die(
            f"{pyproject} has no [tool.setuptools_scm] section - this script "
            "assumes setuptools_scm-based versioning"
        )
    version_file = scm.get("version_file")
    if not version_file:
        die(f"[tool.setuptools_scm] in {pyproject} has no version_file set")
    return Path(version_file)


def changelog_contains_version(version: str, path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text()
    patterns = [
        rf"(?m)^##\s+\[?v?{re.escape(version)}\]?\b",
        rf"(?m)^#\s+\[?v?{re.escape(version)}\]?\b",
    ]
    return any(re.search(p, text) for p in patterns)


def confirm_changelog(version: str, path: Path) -> None:
    if not path.exists():
        print(f"No {path} found in this repo; skipping changelog check.")
        return

    if changelog_contains_version(version, path):
        print(f"{path} already contains a section for v{version}.")
        return

    print(f"{path} does not obviously contain a section for v{version}.")
    while True:
        answer = input(
            f"Has {path} been updated with a '## v{version}' section for this release? [y/n] "
        ).strip().lower()
        if answer in {"y", "yes"}:
            return
        if answer in {"n", "no"}:
            die(f"update {path} first, then rerun this script")


def confirm_tests_run() -> None:
    answer = input(
        "Have you run the full/expensive test suite for this release "
        "(not just what CI runs on every commit)? [y/n] "
    ).strip().lower()
    if answer not in {"y", "yes"}:
        die("run the full test suite first, then rerun this script")


def run_if_present(script: Path, args: list, *, pixi_env: str) -> None:
    if not script.exists():
        return
    print(f"Running {script}")
    run(["pixi", "run", "-e", pixi_env, "python3", str(script), *args])


def write_version_files(version: str, pixi_env: str) -> None:
    print(f"Force-writing version files for v{version} via setuptools_scm")
    run(
        [
            "pixi",
            "run",
            "-e",
            pixi_env,
            "bash",
            "-c",
            f"SETUPTOOLS_SCM_PRETEND_VERSION={version} "
            "python -m setuptools_scm --force-write-version-files",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare a release for a bird-suite Python (setuptools_scm) package."
    )
    parser.add_argument("--version", required=True, help="Release version, e.g. 0.21.4")
    parser.add_argument("--tag-prefix", default="v", help='Git tag prefix; default "v"')
    parser.add_argument("--pixi-env", default="dev", help="pixi environment to run commands in")
    parser.add_argument(
        "--no-commit", action="store_true", help="Modify files but do not commit or tag"
    )
    parser.add_argument(
        "--allow-dirty", action="store_true", help="Allow running with an already-dirty git tree"
    )
    parser.add_argument(
        "--skip-changelog-check", action="store_true", help="Skip the CHANGELOG.md confirmation"
    )
    parser.add_argument(
        "--skip-tests-confirmation",
        action="store_true",
        help="Skip the 'have you run the full test suite' prompt",
    )
    parser.add_argument(
        "--skip-dep-defs",
        action="store_true",
        help="Skip admin/build_dep_defs_from_pixi.py even if present",
    )
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        help="Skip admin/build_docs.py even if present",
    )
    args = parser.parse_args()

    version = args.version
    tag = f"{args.tag_prefix}{version}"

    validate_version(version)

    if not args.allow_dirty:
        check_clean_git()

    existing_tags = capture(["git", "tag", "--list", tag])
    if existing_tags:
        die(f"git tag {tag!r} already exists")

    if not args.skip_tests_confirmation:
        confirm_tests_run()

    if not args.skip_changelog_check:
        confirm_changelog(version, Path("CHANGELOG.md"))

    version_file = get_version_file(Path("pyproject.toml"))
    print(f"Version file (from pyproject.toml): {version_file}")

    if not args.skip_dep_defs:
        run_if_present(Path("admin/build_dep_defs_from_pixi.py"), [], pixi_env=args.pixi_env)

    if not args.skip_docs:
        run_if_present(
            Path("admin/build_docs.py"), ["--version", version], pixi_env=args.pixi_env
        )

    # Docs/dep-def generation may have touched files; re-check before tagging,
    # same guard singlem's existing release script uses.
    if not args.allow_dirty:
        status = capture(["git", "status", "--porcelain"])
        if status and status.strip() != f" M {version_file}":
            print("Working tree changed by the steps above:")
            print(status)
            # version_file itself is expected to change next; anything else is not.

    write_version_files(version, args.pixi_env)

    if args.no_commit:
        print()
        print("Stopped before commit/tag because --no-commit was supplied.")
        print("Review changes with:")
        print("  git diff")
        return

    run(["git", "commit", "-a", "-m", f"v{version}"])
    run(["git", "tag", tag])

    print()
    print(f"Committed and tagged {tag}.")
    print("Now run:")
    print("  git push && git push --tags")
    print("GitHub Actions will then build and upload to PyPI.")
    print("Once on PyPI, also update the bioconda recipe / submit a PR to bioconda-recipes,")
    print("and verify deployment via any downstream installation-check repo if one exists.")


if __name__ == "__main__":
    main()
