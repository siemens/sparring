#!env python

# Copyright (c) Siemens AG, 2013
#
# This file is part of sparring.  sparring is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2
# of the License, or(at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from distutils.core import setup
setup(name='sparring',
      author='Siemens CERT'
      author_email='cert@siemens.com',
      version='0.1',
      description='Network simulation for malware analysis',
      license='GPLv2',
      platforms='linux2',
      url='https://github.com/siemens/sparring',
      packages=['sparring','sparring.applications', 'sparring.lib', 'sparring.transports', 'sparring.utils'],
      package_dir={'sparring': 'sparring',
                   'sparring.applications': 'sparring/applications',
                   'sparring.transports': 'sparring/transports',
                   'sparring.utils': 'sparring/utils',
                   'sparring.lib': 'sparring/lib'},
      data_files=[('/usr/share/sparring', ['sparring/scripts/transparent.sh']),
                  ('/usr/share/sparring', ['sparring/scripts/halffull.sh'])],

)
