import os
from os.path import dirname, join
import io
from setuptools import setup

def get_version(relpath):
  """Read version info from a file without importing it"""
  for line in io.open(join(dirname(__file__), relpath), encoding="cp437"):
    if "__version__" in line:
      if '"' in line:
        return line.split('"')[1]
      elif "'" in line:
        return line.split("'")[1]

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_readme():
    with open(os.path.join(ROOT_DIR, 'README.md')) as fh:
        return ''.join(fh.readlines())

setup(
    name='bird_tool_utils',
    version=get_version('bird_tool_utils/version.py'),
    url='https://github.com/wwood/bird_tool_utils-python/',
    license='GPL3+',
    author='Ben Woodcroft, Rhys Newell',
    author_email='benjwoodcroft@gmail.com, rhys.newell@hdr.qut.edu.au',
    maintainer='Ben Woodcroft',
    maintainer_email='benjwoodcroft@gmail.com',
    packages=['bird_tool_utils'],
    description='Python utilities used as part of the bird suite of bioinformatic tools',
    long_description=get_readme(),
    long_description_content_type='text/markdown',
    package_data={'': [
            "bird_tool_utils/*",
                       ]},
    data_files=[(".", ["README.md", "LICENCE.txt"])],
    include_package_data=True,
    install_requires=(
      'argparse-manpage-birdtools >= 1.6'
    ),
    setup_requires=['nose >= 1.0'],
    test_suite='nose.collector',
)
