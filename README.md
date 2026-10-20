[![Travis](https://api.travis-ci.com/wwood/bird_tool_utils-python.svg?branch=main)](https://travis-ci.com/wwood/bird_tool_utils-python)

A set of Python utilities used as part of the bird suite of bioinformatic tools,
developed by the Woodcroft research lab at the Centre for Microbiome Research at
the Queensland University of Technology. The classes and functions inside are
often heavily opinionated to reduce downstream coding effort and to standardise
UI. They may change without warning.

Current utilities:

* `SeqReader().readf[aq]` - pure python generator function for reading FASTA / FASTQ files
* `BirdArgparser` - opinionated way of presenting help messages - default help prints examples with colour, `--full-help` shows a man page. `--full-help-roff` can be used to generate HTML versions. Logging arguments are batteries included. Subcommands that should run without additional arguments can be created with `allow_no_args=True`.
* `table_roff` for generating ROFF format tables for use with `BirdArgparser`
* `in_working_directory` and `in_tempdir` are context functions for temporary switching to a directory
* `iterable_chunks` provides chunking for iterables

## Release capabilities

Alongside the library, this package ships a shared release tool for the bird
suite's Python packages. Any package that uses `setuptools_scm` versioning can
be released the same way, instead of each tool carrying its own copy of a
hand-rolled `admin/release.py` that slowly drifts from the others.

    cd path/to/the/tool            # the tool's repo root, not this one
    pixi run -e dev bird-release-python --version X.Y.Z # Version of the tool release

`bird-release-python` is a console script installed with this package, so a
tool only needs `bird_tool_utils_python` (aviary, isiteuk and
singlem already have it). Use `--help` for the full flag list.

### What it does

In order, and stopping at the first failure:

1. Validates the version and refuses a dirty git tree or an existing tag.
2. Runs the default (fast, non-expensive) `pytest` suite, then asks whether the
   full/expensive suite was run, since that takes hours and can't run inline.
3. Checks `CHANGELOG.md` for a `## vX.Y.Z` section.
4. Asks the tool's own yes/no confirmations, then runs the tool's own steps
   (both declared in its `pyproject.toml`, below).
5. Aborts if those steps left unexpected changes in the working tree.
6. Writes the new version into the tool's `version.py` through `setuptools_scm`.
7. Commits `vX.Y.Z`, creates the tag `vX.Y.Z`, and prints the tool's reminders.

**It never pushes.** Pushing the tag is what triggers the tool's publish
workflow (PyPI), so that step is deliberately left to the user.

### Per-tool configuration

Everything the shared script needs to know about a tool lives in the tool's
own `pyproject.toml`, so nothing tool-specific is hardcoded here:

```toml
[tool.setuptools_scm]
version_file = "mytool/version.py"      # where the script writes the version

[tool.bird_release]
steps = ["admin/build_dep_defs_from_pixi.py"]    # run in order; missing file = hard error
confirmations = ["Is docs/SKILL.md up to date?"]  # asked up front; anything but yes aborts
reminders = ["Build and push the Docker image"]   # printed after commit + tag
```

A declared step whose file is missing fails the release rather than being
skipped, so a renamed script can't silently stop running while the tag ships.
Steps and reminders accept `{version}`. If `[tool.bird_release]` is absent the
script says so and runs only the shared steps.

### Releasing safely

Run the script on the PR's feature branch, push the branch so the `vX.Y.Z`
commit is part of the PR, merge with **"Create a merge commit"** (never squash
or rebase, which would leave the tag pointing at a commit that is not in
`main`), and only then push the tag: `git push && git push --tags`.
Where `main` is branch-protected this order is required, because the release
commit can only reach `main` inside a PR.

### AI-assisted releases

The repo includes Claude Code guidance in `.claude/`: `CLAUDE.md` and the
`python-packaging` skill (`.claude/skills/python-packaging/`), with templates
for a tool's `CHANGELOG.md` and `[tool.bird_release]` block. They let an AI
assistant prepare a release (check the tool's declared steps, the changelog
and hand-written version strings, run the script) while the final steps stay
manual: the assistant hands over, and a person decides when to push, merge and
tag.

### Tool templates

`.claude/tools_templates/` holds one markdown file per tool for the details
that are specific to that tool: its reminders, hand-written version strings
and extra requirements/constraints. This keeps every special case in one place, so a tool's
quirks can be updated without touching the shared script. Aviary and isiteuk
are covered; SingleM is not implemented yet.
