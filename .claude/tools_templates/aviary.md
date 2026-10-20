# Aviary release template

Tool-specific details for releasing **aviary** with `bird-release-python`.
The shared flow is in the `python-packaging` skill; this file holds only what
is particular to aviary. Always re-read the repo's own `[tool.bird_release]`
before relying on this: that table is the source of truth, this is the guide.

| | |
| --- | --- |
| Repo (upstream) | `rhysnewell/aviary` (remote `upstream`) |
| PyPI name | `aviary-genome` |
| Version file | `aviary/version.py` (setuptools_scm, `version_scheme = "only-version"`) |
| Publish workflow | `.github/workflows/python-publish.yml`, fires on a `v*` tag push |
| Default pixi env | `dev` |

## Declared in aviary's `[tool.bird_release]`

| Kind | Entry |
| --- | --- |
| steps | `admin/build_dep_defs_from_pixi.py` |
| confirmations | "Is docs/SKILL.md up to date for this release?" |
| reminders | Build and push the Docker image; "Do Manual Aviary Release" |

aviary has no docs-building step. Docs deploy from `deploy-docs.yaml` pushing to the doc branch, not at release time.

## Branch protection: the order is not optional

`main` on `rhysnewell/aviary` is protected ("changes must be made through a
pull request"). The release commit can only reach `main` inside a PR.

1. Branch is level with upstream:
   `git fetch upstream --tags && git merge upstream/main`, then
   `git rev-list --count HEAD..upstream/main` must print `0`.
2. All work committed first: the code, the changelog section, and the
   hand-written version strings (below). PR open, CI green.
3. Release commit last, on the same branch:
   `pixi run -e dev bird-release-python --version X.Y.Z`, then
   `git push origin <branch>`.
4. Merge the PR with **"Create a merge commit"**. Never squash or rebase. This way to keep the commit id with the release id. 
5. Push the tag: `git push && git push --tags`.

The script prints `git push && git push --tags` at the end; that is the
command to use in step 5, once the PR has been merged.

The tag push publishes to PyPI, which cannot be undone. Do it only after the
merge, so PyPI and `main` cannot disagree.

## CHANGELOG

- Heading must be exactly `## vX.Y.Z - YYYY-MM-DD` and non-empty. The GitHub
  release draft copies this section into the notes.
- Write plain user-facing prose; the section is pasted into the release as is.

## Hand-written version strings

The script does **not** touch these. Grep for the previous version and update
them in the PR before running the script:

| File | Line to check |
| --- | --- |
| `docs/SKILL.md` | "Latest version" line (~12) |
| `README.md` | apptainer pull and run examples (~142, ~171) |
| `docker/Dockerfile.sh` | `git checkout vX.Y.Z` (~20) and `pip install aviary-genome==X.Y.Z` (~26) |
| `docker/README.md` | `AVIARY_VERSION=` (~17) |

Line numbers drift; search for the old version string rather than trusting them.
At the time of writing several of these lag the latest release.

Never commit the postinstall-stamped `commit_id` in `version.py`. Upstream's
committed value is `None`, and the release script writes it that way.

## After the tag push

1. **GitHub release.** If the `github-release` job is on `main`, a draft
   release is created automatically from the changelog section, the PyPI
   sha256 and the compare link: review it and press Publish. If the job is
   not on `main` yet, create the release by hand from the tag.
2. **Docker.** `pixi run postinstall`, then `pixi run bash docker/build.sh`,
   then run the `docker push` lines it prints. Do not push the image until
   the known `/root/.cache` leak in the catch-all `COPY` layer of
   `docker/Dockerfile.in` is fixed (`rm -rf /root/.cache`).
3. **bioconda.** The bot opens a version-bump PR; check and merge it. It works
   out the sha256 itself.

## Do not

- Hand-edit `aviary/version.py`; it is regenerated from the tag.
- Use `.github/workflows/release.yml` (if present): it pushes straight to
  `main`, which branch protection rejects.
- Push a tag from a release commit that is not in `main`'s history. This is messy
- Do not also send any --tags command, give these to the user to submit. 
