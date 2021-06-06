import os
import contextlib
from pathlib import Path
import tempfile

from .argparsing import *


@contextlib.contextmanager
def in_working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


@contextlib.contextmanager
def in_tempdir():
    '''Create a new temporary directory and chdir there as a context i.e. chdir
    back when finished'''

    with tempfile.TemporaryDirectory() as tmpdirname:
        with in_working_directory(tmpdirname):
            yield


def table_roff(table):
    roff = "\n.TS\ntab(@);\n"
    for row in table:
        for col in row:
            roff += 'l '
        break
    roff += '.\n'

    first_row = True
    for row in table:
        first_column = True
        for cell in row:
            if first_column:
                first_column = False
            else:
                roff += '@'
            roff += 'T{\n'
            roff += cell
            roff += '\nT}'
        roff += '\n'
        if first_row:
            first_row = False
            roff += "_\n"
    roff += '.TE\n'
    return roff