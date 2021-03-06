###############################################################################
##
##  Copyright 2013 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from setuptools import setup, find_packages

LONGSDESC = """
A Simple Register Device Protocol (SRDP) library for the Twisted networking framework.
"""

## get version string from "srdp/_version.py"
## See: http://stackoverflow.com/a/7071358/884770
##
import re
VERSIONFILE="srdp/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
   verstr = mo.group(1)
else:
   raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))


setup (
   name = 'srdp',
   version = verstr,
   description = 'Simple Register Device Protocol (SRDP) library.',
   long_description = LONGSDESC,
   license = 'Apache License 2.0',
   author = 'Tavendo GmbH',
   url = 'https://github.com/tavendo/SRDP',
   platforms = ('Any'),
   install_requires = ['setuptools',
                       'zope.interface>=3.6.0',
                       'Twisted>=11.1',
                       'crcmod>=1.7',
                       'pyserial>=2.6'],
   packages = find_packages(),
   #packages = ['srdp'],
   include_package_data = True,
   package_data = {
      '': ['templates/*.html'],
    },
   zip_safe = False,
   entry_points = {
      'console_scripts': [
         'srdptool = srdp.srdptool:run'
      ]},
   ## http://pypi.python.org/pypi?%3Aaction=list_classifiers
   ##
   classifiers = ["License :: OSI Approved :: Apache Software License",
                  "Development Status :: 3 - Alpha",
                  "Environment :: Console",
                  "Framework :: Twisted",
                  "Intended Audience :: Developers",
                  "Operating System :: OS Independent",
                  "Programming Language :: Python",
                  "Topic :: Internet",
                  "Topic :: Home Automation",
                  "Topic :: Software Development :: Libraries",
                  "Topic :: Software Development :: Embedded Systems",
                  "Topic :: Software Development :: Testing"],
   keywords = 'srdp embedded mcu realtime'
)
