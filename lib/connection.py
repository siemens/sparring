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

from Queue import Queue
import cStringIO
from socket import inet_ntoa

class Connection():
  def __init__(self, transport, (l, lport), (r, rport), module = None):
    self.transport = transport
    self.module = module
    self.outgoing = cStringIO.StringIO()
    self.outqueue = Queue()
    self.incoming = cStringIO.StringIO()
    self.inqueue = Queue()
    self.local = (l, lport)
    self.remote = (r, rport)
    self.proxy = None
    self.in_extra = None # Optional information assigned by self.module routines
    self.out_extra = None # Optional information assigned by self.module routines

  def put_in(self, t):
    """ add new data to the buffer """
    self.incoming.write(t)

  def put_out(self, t):
    """ add new data to the buffer """
    self.outgoing.write(t)

  def handle(self):
    if self.module:
      self.module.handle(self)

  def classify(self):
    """ Does nothing if module is already set
    i.e. if this connection has been classified before
    """
    if self.module:
      return True
    if self.transport:
      return self.transport.classify(self)
    return False

  def __str__(self):
    l = inet_ntoa(self.local[0])
    r = inet_ntoa(self.remote[0])
    
    return '%s:%i - %s:%i' % (l, self.local[1], r, self.remote[1])
