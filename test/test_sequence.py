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
import tempfile

sys.path = [os.path.join(os.path.dirname(os.path.realpath(__file__)),'..')]+sys.path

import bird_tool_utils
from bird_tool_utils import BirdHelpFormatter
from bird_tool_utils import *

class Tests(unittest.TestCase):
    maxDiff = None
    
    def test_readfa(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(">seq 1\nATG\nATG\n>5\nAAA\n".encode())
            f.flush()

            self.assertEqual(
                [('seq','ATGATG'),('5','AAA')],
                list(SeqReader().readfa(open(f.name)))
                )
        
if __name__ == "__main__":
    unittest.main()
