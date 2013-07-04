# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.

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

