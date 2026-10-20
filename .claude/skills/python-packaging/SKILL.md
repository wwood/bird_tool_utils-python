---
name: python-packaging
description: >-
  Package and release a bird-suite Python tool (aviary, singlem,
  bird_tool_utils, isiteuk) the setuptools_scm +
  `bird-release-python` way. Use when setting up or migrating a package to
  these conventions, declaring its per-tool release steps / confirmations /
  reminders, or preparing a release. The Python counterpart of the
  rust-packaging skill in wwood/bird_tool_utils-rust.
---

# Python packaging & release (the `bird-release-python` way)

Templates live in `templates/` next to this file. Copy them into the target
package and fill in the placeholders instead of writing them from scratch.

## The one rule: per-tool lists live in the tool

`bird_tool_utils/release.py` (console script `bird-release-python`) holds only
what every tool shares: default tests, the changelog check, the version write,
the commit and the tag. Everything specific to one tool is declared in **that
tool's own** `[tool.bird_release]` table in its `pyproject.toml`
(`templates/pyproject.snippet.toml`):

| Key             | Meaning                                                      |
| --------------- | ------------------------------------------------------------ |
| `steps`         | Scripts run in order via `pixi run -e dev python3 <step>`; a missing file is a hard error |
| `confirmations` | Yes/no questions asked up front; any answer but yes aborts   |
| `reminders`     | Printed after commit+tag, e.g. aviary's "Do Manual Aviary Release" |

**Never hardcode one tool's steps, questions or reminders into another, or into
the shared script.** Before advising on a release, read the target repo's
`[tool.bird_release]` and report exactly what it declares. An absent table
means "declared nothing", and the script says so; do not assume anything.

## Setting up / migrating a package

1. `pyproject.toml`: `dynamic = ["version"]`, `setuptools_scm` in
   `[build-system].requires`, and the `[tool.setuptools_scm]` and
   `[tool.bird_release]` blocks from the snippet. Keys match the rest of the
   suite, so all packages release identically.
2. `version.py` is tracked in git and rewritten by the release script; never
   hand-edit it.
3. `CHANGELOG.md`: copy `templates/CHANGELOG.md`. Headings are `## vX.Y.Z -
   YYYY-MM-DD` with `### Added` / `### Fixed` / `### Changed`. There is no
   `Unreleased` section here; write the `## vX.Y.Z` section before releasing.
4. The tool's own publish workflow (already in each repo) builds on tag push.
   It needs `fetch-depth: 0`, or setuptools_scm publishes 0.0.0.
5. Declare `steps` / `confirmations` / `reminders` for this tool, with a
   comment for any deliberate absence.

## Release process

Run from the **target package's** repo root:

    pixi run -e dev bird-release-python --version X.Y.Z

It: validates the version, refuses a dirty tree or existing tag, runs the
default pytest suite, asks whether the full/expensive suite was run, confirms
the changelog, asks the tool's `confirmations`, runs its `steps`, force-writes
`version.py`, commits `vX.Y.Z` and tags it. **It never pushes.**

### Order matters

The user must run the release script **on the PR's feature branch, before the
PR is merged**, and the PR must then be merged with **"Create a merge commit"**.
That way the `vX.Y.Z` release commit rides inside the PR and lands on main
unchanged, so the `vX.Y.Z` tag points at a commit that exists on main.

1. On the feature branch (not main), run `bird-release-python`. It commits
   `vX.Y.Z` and creates the tag locally.
2. Push the branch (`git push`) so the PR contains the release
   commit to main.
3. Merge the PR with **"Create a merge commit"**. Never squash or rebase: both
   rewrite the commit, which orphans the tag and breaks the version. If you can't do this step, report to user that PR needs to be merged first before pushing the tag.
4. Push the tag (`git push && git push --tags`). The tag push triggers the publish
   workflow, and the release to PyPI occurs.
5. Report the tool reminders to the user, e.g. "Do Manual Aviary Release".

If the release commit was made after the PR merged, or the PR was squashed, the
tag does not match main. Stop and tell the user rather than pushing the tag.

## Hand-written version strings

`bird-release-python` only rewrites `version.py`. Strings written by hand (a
"Latest version" line in docs, a container tag in the README, FAQ wording)
go stale. Grep for the previous version before releasing and fix them, or add
a `confirmations` question for the ones that matter.

## Assistant rules

- Prepare and hand over; do not push, tag-push or publish without the user's
  explicit go-ahead each time.
- Confirm before editing existing files; creating new ones is fine.
- Commit messages: `<type>: <description>` (feat, fix, refactor, docs, test,
  chore, perf, ci).
- Always check the target repo's `[tool.bird_release]` for its own steps, questions and reminders. Do not assume anything.
- If unsure, ask the user to confirm before proceeding. Don't make assumptions about the target repo's state or contents.

## Verification checklist

- [ ] `[tool.setuptools_scm]` and `[tool.bird_release]` present in `pyproject.toml`.
- [ ] Every declared `steps` path exists.
- [ ] `CHANGELOG.md` has a `## vX.Y.Z` section.
- [ ] Hand-written version strings checked.
- [ ] The publish workflow has `fetch-depth: 0`.
- [ ] Release commit is on the PR branch before merge.
