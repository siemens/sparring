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

from cStringIO import StringIO

# truncate _cStringIO_ objects
def ltruncate(f, bytes=None):
  """ truncate given cStringIO object from the left
  if bytes is an integer, truncate bytes many byte from f,
  otherwise truncates f.tell() many bytes from f """

  if bytes != None:
    from os import SEEK_SET
    f.seek(bytes, SEEK_SET)

  h = StringIO()
  h.write(f.read())
  f.close()
  del f
  return h

