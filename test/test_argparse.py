#!/usr/bin/env python3

#=======================================================================
# Authors: Ben Woodcroft
#
# Unit tests.
#
# Copyright
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License.
# If not, see <http://www.gnu.org/licenses/>.
#=======================================================================

import unittest
import os.path
import sys
import io
import contextlib

sys.path = [os.path.join(os.path.dirname(os.path.realpath(__file__)),'..')]+sys.path

import bird_tool_utils
from bird_tool_utils import BirdHelpFormatter
from bird_tool_utils import *

class Tests(unittest.TestCase):
    maxDiff = None
    
    def test_str2bool(self):
        self.assertEqual(True, str2bool('y'))
        self.assertEqual(False, str2bool('false'))

    def test_allow_no_args_subparser(self):
        saved = sys.argv
        parser = BirdArgparser(program='TestProgram', program_invocation='testprog')
        parser.new_subparser('build', 'desc', allow_no_args=True)
        sys.argv = ['testprog', 'build']
        try:
            args = parser.parse_the_args()
            self.assertFalse(args.debug)
        finally:
            sys.argv = saved

    def test_default_requires_args(self):
        saved = sys.argv
        parser = BirdArgparser(program='TestProgram', program_invocation='testprog')
        parser.new_subparser('build', 'desc')
        sys.argv = ['testprog', 'build']
        try:
            with self.assertRaises(SystemExit):
                parser.parse_the_args()
        finally:
            sys.argv = saved

    def test_exclude_group_not_in_help(self):
        saved = sys.argv
        parser = BirdArgparser(program='TestProgram', program_invocation='testprog')
        parser.new_subparser('hidden', 'hidden desc', parser_group='exclude')
        parser.new_subparser('shown', 'shown desc')
        sys.argv = ['testprog', '-h']
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit):
                    parser.parse_the_args()
            output = buf.getvalue()
            self.assertNotIn('hidden', output)
            self.assertIn('shown', output)
        finally:
            sys.argv = saved

    def test_long_description_wraps(self):
        saved = sys.argv
        parser = BirdArgparser(program='TestProgram', program_invocation='testprog')
        long_desc = ' '.join(['desc'] * 50)
        parser.new_subparser('build', long_desc)
        sys.argv = ['testprog', '-h']
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit):
                    parser.parse_the_args()
            output_lines = buf.getvalue().splitlines()
            for i, line in enumerate(output_lines):
                if line.strip().startswith('build'):
                    desc_start = line.index('desc')
                    self.assertLessEqual(len(line), 120)
                    self.assertTrue(output_lines[i+1].startswith(' ' * desc_start))
                    break
            else:
                self.fail('build subcommand not found in help output')
        finally:
            sys.argv = saved
        
if __name__ == "__main__":
    unittest.main()
