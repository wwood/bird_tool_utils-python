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

Exposed as the `bird-release-python` console script (see [project.scripts] in
pyproject.toml). Run from the target package's own repository root, e.g.:
    cd ~/singlem-myversion && pixi run -e dev bird-release-python --version 0.21.4
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
    if path.exists() and changelog_contains_version(version, path):
        print(f"{path} already contains a section for v{version}.")
    elif path.exists():
        print(f"{path} does not obviously contain a section for v{version}.")
    else:
        print(f"No {path} found in this repo.")

    # Asked every time, regardless of the detection above: a heading can exist
    # while saying nothing about this release's actual changes.
    #
    # Only the changelog is asked about here. Documentation questions are
    # package-specific (singlem cares about SKILL.md.in, aviary does not) and
    # belong in that package's [tool.bird_release].confirmations, not baked
    # into the shared script where every tool inherits every other tool's
    # conventions.
    while True:
        answer = input(
            f"Has {path} been updated with a '## v{version}' section "
            "describing this release? [y/n] "
        ).strip().lower()
        if answer in {"y", "yes"}:
            return
        if answer in {"n", "no"}:
            die(f"update {path} first, then rerun this script")


def run_default_tests(pixi_env: str) -> None:
    # The same fast, non-expensive tier CI already runs on every commit (no
    # --run-expensive/--run-qsub/--run-download) -- a real, automatic sanity
    # check, not a trust-based prompt. Runs in under a couple of minutes for
    # both singlem and aviary, so it's cheap enough to always run here.
    print("Running default (non-expensive) test suite...")
    try:
        run(["pixi", "run", "-e", pixi_env, "pytest", "-v"])
    except subprocess.CalledProcessError:
        die("default test suite failed; fix the failures, then rerun this script")


def confirm_tests_run() -> None:
    answer = input(
        "Have you also run the full/expensive test suite for this release "
        "(e.g. `pytest --run-expensive`/`--run-qsub`; this is separate from "
        "the default suite just run automatically above, and can't be run "
        "inline here since it takes hours -- database-download tests behind "
        "`--run-download` are a separate concern and not required here)? [y/n] "
    ).strip().lower()
    if answer not in {"y", "yes"}:
        die("run the full test suite first, then rerun this script")


def load_release_config(pyproject: Path) -> dict:
    """Read the target package's [tool.bird_release] block, if any.

    Absent is allowed -- a package may genuinely have no per-release steps --
    but it is REPORTED rather than silently assumed, so "declared nothing" and
    "forgot to declare" don't look identical in the output.
    """
    data = tomllib.loads(pyproject.read_text())
    config = data.get("tool", {}).get("bird_release")
    if config is None:
        print(
            f"No [tool.bird_release] in {pyproject}: no per-package steps, "
            "confirmations or reminders will run."
        )
        return {}
    return config


def run_declared_steps(steps: list, version: str, *, pixi_env: str) -> None:
    """Run each declared step, failing hard if its script is missing.

    Deliberately NOT filesystem autodetection. An earlier draft globbed for
    well-known paths (admin/build_dep_defs_from_pixi.py, admin/build_docs.py)
    and skipped whatever was absent, which meant a renamed or mistyped script
    silently stopped running at release time while the tag shipped anyway --
    "skipped" and "nothing to do" printed the same nothing. singlem's original
    per-tool release script ran its steps unconditionally and died if one was
    missing; declaring them here keeps that failure mode while still letting
    each package own its own list.

    Each entry is a command string relative to the repo root, with {version}
    substituted, e.g. "admin/build_docs.py --version {version}".
    """
    if not steps:
        print("No [tool.bird_release] steps declared.")
        return
    for step in steps:
        parts = step.format(version=version).split()
        script = Path(parts[0])
        if not script.exists():
            die(
                f"declared release step {parts[0]!r} does not exist. Fix the path "
                "in [tool.bird_release].steps, or remove the step if it no longer "
                "applies -- it is not skipped automatically."
            )
        print(f"Running declared step: {step}")
        run(["pixi", "run", "-e", pixi_env, "python3", *parts])


def confirm_declared(confirmations: list) -> None:
    """Ask each package-declared yes/no question; anything but yes aborts.

    These are the per-tool equivalents of singlem's hardcoded "Did you check
    SKILL.md.in is up to date?" -- questions only that package's maintainers
    can write, so they live in that package's pyproject.toml rather than in
    this shared script.
    """
    for question in confirmations:
        answer = input(f"{question} [y/n] ").strip().lower()
        if answer not in {"y", "yes"}:
            die(f"answered no to: {question}")


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
        "--skip-tests",
        action="store_true",
        help="Skip actually running the default (non-expensive) pytest suite",
    )
    parser.add_argument(
        "--skip-tests-confirmation",
        action="store_true",
        help="Skip the 'have you run the full/expensive test suite' prompt",
    )
    parser.add_argument(
        "--skip-steps",
        action="store_true",
        help="Skip the [tool.bird_release].steps declared by this package",
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

    if not args.skip_tests:
        run_default_tests(args.pixi_env)

    if not args.skip_tests_confirmation:
        confirm_tests_run()

    if not args.skip_changelog_check:
        confirm_changelog(version, Path("CHANGELOG.md"))

    version_file = get_version_file(Path("pyproject.toml"))
    print(f"Version file (from pyproject.toml): {version_file}")

    release_config = load_release_config(Path("pyproject.toml"))

    confirm_declared(release_config.get("confirmations", []))

    if not args.skip_steps:
        run_declared_steps(
            release_config.get("steps", []), version, pixi_env=args.pixi_env
        )

    # Docs/dep-def generation may have touched files unexpectedly; hard-abort
    # before tagging if so, same guard singlem's original release script used
    # (it ran a plain `exit 1` here). version_file itself is expected to
    # change next via write_version_files(), so that alone is fine.
    if not args.allow_dirty:
        status = capture(["git", "status", "--porcelain"])
        if status and status.strip() != f" M {version_file}":
            print("Working tree changed unexpectedly by the steps above:")
            print(status)
            die(
                f"repo is not clean after dep-defs/docs generation; if a tag "
                f"{tag!r} was already created, remove it with `git tag -d {tag}` "
                "before investigating and rerunning"
            )

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
    print("REMINDER: Don't forget to update and do a release on GitHub!")

    # Everything beyond the two universal reminders above is package-specific
    # (does this tool ship a Docker image? does it have a bioconda recipe? is
    # there an installation-check repo?) and is declared by the package rather
    # than guessed at from the filesystem here. Previously this block named
    # aviary and singlem directly, so every tool using this script inherited
    # every other tool's post-release steps as noise.
    for reminder in release_config.get("reminders", []):
        print(f"REMINDER: {reminder.format(version=version)}")


if __name__ == "__main__":
    main()
