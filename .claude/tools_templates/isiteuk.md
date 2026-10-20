# isiteuk release template

Tool-specific details for releasing **isiteuk** with the bird-suite release
flow. The shared flow is in the `python-packaging` skill; this file holds only
what is particular to isiteuk.

## What it is

isiteuk classifies genomes by domain (Bacteria, Archaea, Eukaryota) using SingleM marker genes.

## Releasing

Instead of calling the shared script directly
(`pixi run -e dev bird-release-python --version "$version"`), run isiteuk's own
wrapper from the repo root:

    admin/release.sh <version>

for example `bash admin/release.sh 0.1.2`.

The release is then finished by hand. Nothing is pushed for you:

    git push && git push --tags

Check the release commit and tag it created (`git log -1`, `git tag --list`)
before running that.
