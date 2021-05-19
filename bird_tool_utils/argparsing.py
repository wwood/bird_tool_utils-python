import argparse


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