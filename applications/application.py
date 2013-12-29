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

import logging

class Application():
  def __init__(self, mode):
    self.mode = mode
    self.handle_ = None
    self.stats = None
    self.protos = []

    if self.mode == 'TRANSPARENT':
      self.handle_ = self.handle_transparent
    elif self.mode == 'HALF':
      self.handle_ = self.handle_half
    elif self.mode == 'FULL':
      self.handle_ = self.handle_full
    log = logging

  def classify(self, conn):
    """try to classify the specified connection
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle(self, conn):
    self.handle_(conn)
    #if self.mode == 'TRANSPARENT':
    #  self.handle_transparent(conn)
    #elif self.mode == 'HALF':
    #  self.handle_half(conn)
    #elif self.mode == 'FULL':
    #  self.handle_full(conn)
  
  def handle_transparent(self, conn):
    """handle data in transparent mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle_half(self, conn):
    """handle data in half mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def handle_full(self, conn):
    """handle data in full mode.
    @raise NotImplementedError: this method is abstract.
    """
    raise NotImplementedError

  def get_stats(self):
    return self.stats

  def protocols(self):
    return self.protos

  def setup(self, conn):
    """this function is meant to be called after a successful protocol
    identification for setting up the required entries in self.conn etc.
    """
    conn.in_extra = {}
    if self.mode == 'TRANSPARENT':
      pass
    elif self.mode == 'HALF':
      conn.in_extra['buffer'] = ""
      # close this connection
      conn.in_extra['close'] = False
    elif self.mode == 'FULL':
      conn.in_extra['buffer'] = ""
      # close this connection
      conn.in_extra['close'] = False

