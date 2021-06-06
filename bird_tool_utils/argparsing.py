import os
import argparse
import sys
import logging
import tempfile
import subprocess
import textwrap

from build_manpages.manpage import Manpage


def str2bool(v):
    '''String to Boolean for better handling of argparse flags that take a true
    or false optionally'''

    if isinstance(v, bool):
        return(v)
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return(True)
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return(False)
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


class BirdHelpFormatter(argparse.HelpFormatter):
    '''Custom help formatter for prettier argparse messages'''

    def _split_lines(self, text, width):
        return text.splitlines()

    def _get_help_string(self, action):
        h = action.help
        if '%(default)' not in action.help:
            if action.default != '' and \
               action.default != [] and \
               action.default != None \
               and action.default != False:
                if action.default is not argparse.SUPPRESS:
                    defaulting_nargs = [argparse.OPTIONAL,
                                        argparse.ZERO_OR_MORE]
                    if action.option_strings or action.nargs in defaulting_nargs:
                        if '\n' in h:
                            lines = h.splitlines()
                            lines[0] += ' [default: %(default)s]'
                            h = '\n'.join(lines)
                        else:
                            h += ' [default: %(default)s]'
        return h

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])

class BirdArgparser:
    '''Introduces a number of opinions into argparse e.g. automatically added
    arguments'''

    FULL_HELP_FLAG = 'full-help'
    FULL_HELP_ROFF_FLAG = 'full-help-roff'

    def __init__(self, **kwargs):
        '''kwargs:

        Required:
        * program: Fully capitalised name e.g. 'SingleM'

        Optional
        * program_invocation: how program is run e.g. 'singlem' [default:
          program.lower()]
        * version: [default dev]
        * authors: list of strings (usually with institution and email). Note
          the people.py in this package [default []]
        * examples: Dict of subcommand name to list of ExampleUsage objects
          [default: {}]
        * raw_format: Use raw ROFF output for --full-help [default False]
        '''
        # Required
        self.program = kwargs.pop('program')

        # Optional
        self.program_invocation = kwargs.pop(
            'program_invocation', self.program.lower())
        self.version = kwargs.pop('version', 'dev')
        self.authors = kwargs.pop('authors', [])
        self.examples = kwargs.pop('examples', {})
        self.raw_format = kwargs.pop('raw_format', False)

        if len(kwargs) > 0:
            raise Exception("Unexpected arguments detected: %s" % kwargs)

        self.parser = argparse.ArgumentParser(add_help=False)
        self._child_parser = argparse.ArgumentParser(parents=[self.parser])
        self._subparser_name_to_parser = {}
        self._subparser_name_to_description = {}

    def new_subparser(self, parser_name, parser_description):
        '''Create a new subparser, and return it. Keep track of all subparsers
        so that they can be referred to with --full-help'''
        if len(self._subparser_name_to_parser) == 0:
            self._subparsers = self._child_parser.add_subparsers(
                title="Sub-commands", dest='subparser_name')
        subparsers = self._subparsers
        subpar = subparsers.add_parser(parser_name,
                                       description=parser_description,
                                       help=parser_description,
                                       parents=[self.parser])
        self._subparser_name_to_parser[parser_name] = subpar
        self._subparser_name_to_description[parser_name] = parser_description
        return subpar

    def _add_boring_common_arguments(self, parser=None):
        if parser is None:
            parser = self.parser
        boring_group = parser.add_argument_group(title='Other general options')
        boring_group.add_argument('--debug', help='output debug information', action="store_true")
        boring_group.add_argument('--version', help='output version information and quit',  action='version', version=self.version)
        boring_group.add_argument('--quiet', help='only output errors', action="store_true")
        boring_group.add_argument('--full-help','--full_help', help='print longer help message', action="store_true")
        boring_group.add_argument('--full-help-roff','--full_help_roff', help='print longer help message in ROFF (manpage) format', action="store_true")

    def parse_the_args(self):
        self._add_boring_common_arguments()
        # Add boring arguments to each subparser
        for (_, subpar) in self._subparser_name_to_parser.items():
            self._add_boring_common_arguments(subpar)

        if '--version' in sys.argv:
            args = self.parser.parse_args()
        elif (len(sys.argv) == 1 or sys.argv[1] == '-h' or sys.argv[1] == '--help'):
            print('')
            print('                ...::: '+self.program+' v' + self.version + ' :::...''')
            print('')
            max_name_length = max([len(name) for name, _ in self._subparser_name_to_description.items()])
            for name, description in self._subparser_name_to_description.items():
                format_string = '  %-{}s  -> {}'.format(max_name_length+2, description)
                print(format_string % name)

            print('\n  Use '+self.program_invocation+' <command> -h for command-specific help.\n'\
                '  Some commands also have an extended --full-help flag.\n')
            sys.exit(0)
        else:
            # Determine whether help was specified before argument parsing.
            print_help = True
            if sys.argv[1] in self._subparser_name_to_parser:
                if '-h' in sys.argv or '--help' in sys.argv or len(sys.argv) == 2:
                    self._print_short_help(sys.argv[1])
                    sys.exit(0)
                elif '--%s' % BirdArgparser.FULL_HELP_FLAG in sys.argv or \
                    '--%s' % BirdArgparser.FULL_HELP_FLAG.replace('-', '_') in sys.argv:
                    self._print_full_help(sys.argv[1])
                    sys.exit(0)
                elif '--%s' % BirdArgparser.FULL_HELP_ROFF_FLAG in sys.argv or \
                    '--%s' % BirdArgparser.FULL_HELP_ROFF_FLAG.replace('-', '_') in sys.argv:

                    subcommand = sys.argv[1]
                    subparser = self._subparser_name_to_parser[subcommand]
                    print(str(self._manpage(subparser)))
                    sys.exit(0)

            # No need for an 'else' here since the above stanzas run sys.exit()
            args = self._child_parser.parse_args()

        if args.debug:
            loglevel = logging.DEBUG
        elif args.quiet:
            loglevel = logging.ERROR
        else:
            loglevel = logging.INFO
        logging.basicConfig(
            level=loglevel, format='%(asctime)s %(levelname)s: %(message)s',
            datefmt='%m/%d/%Y %I:%M:%S %p')

        return args

    def _print_short_help(self, subcommand):
        if subcommand in self.examples:
            width = os.get_terminal_size().columns
            if width > 100:
                width = 100
            print(_bcolors.OKGREEN)
            print(('%s %s' % (
                self.program_invocation,
                subcommand)).center(width))
            print(self._subparser_name_to_description[subcommand].center(width))
            print(_bcolors.ENDC)
            for example in self.examples[subcommand]:
                print('%s%s%s' % (
                    _bcolors.HEADER,
                    '\n'.join(textwrap.wrap('Example: '+example.description, width=width)),
                    _bcolors.ENDC))
                print()
                print('  %s' % example.invocation)
                print()
            print('\nSee %s %s --%s for further options and further detail.\n' % (
                self.program_invocation, subcommand, BirdArgparser.FULL_HELP_FLAG))
        else:
            self._print_long_help(subcommand)

    def _print_full_help(self, subcommand):
        subparser = self._subparser_name_to_parser[subcommand]
        with tempfile.NamedTemporaryFile(
            prefix='{}-manpage-'.format(subcommand)) as f:

            f.write(str(self._manpage(subparser)).encode())
            f.flush()
            subprocess.run('man {}'.format(f.name), shell=True)

    def _manpage(self, parser):
        return Manpage(parser, authors=self.authors, raw_format=self.raw_format)

class Example:
    def __init__(self, description, invocation):
        self.description = description
        self.invocation = invocation

class _bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
