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
