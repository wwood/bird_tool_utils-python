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


class SeqReader:
    # Stolen from https://github.com/lh3/readfq/blob/master/readfq.py
    def readfq(self, fp): # this is a generator function
        '''Generator function for reading FASTQ files'''
        last = None # this is a buffer keeping the last unprocessed line
        while True: # mimic closure; is it a bad idea?
            if not last: # the first record or a record following a fastq
                for l in fp: # search for the start of the next record
                    if l[0] in '>@': # fasta/q header line
                        last = l[:-1] # save this line
                        break
            if not last: break
            name, seqs, last = last[1:].partition(" ")[0], [], None
            for l in fp: # read the sequence
                if l[0] in '@+>':
                    last = l[:-1]
                    break
                seqs.append(l[:-1])
            if not last or last[0] != '+': # this is a fasta record
                yield name, ''.join(seqs), None # yield a fasta record
                if not last: break
            else: # this is a fastq record
                seq, leng, seqs = ''.join(seqs), 0, []
                for l in fp: # read the quality
                    seqs.append(l[:-1])
                    leng += len(l) - 1
                    if leng >= len(seq): # have read enough quality
                        last = None
                        yield name, seq, ''.join(seqs); # yield a fastq record
                        break
                if last: # reach EOF before reading enough quality
                    yield name, seq, None # yield a fasta record instead
                    break

    def readfa(self, fp):
        '''Generator function for reading FASTA files'''
        for (name, seq, _) in self.readfq(fp):
            yield name, seq
