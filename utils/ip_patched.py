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

from dpkt import ip

class ip_patched(ip.IP):
    def __str__(self):
        if self.sum == 0:
            self.sum = dpkt.in_cksum(self.pack_hdr() + self.opts)
            if (self.p == 6 or self.p == 17) and \
               (self.off & (IP_MF|IP_OFFMASK)) == 0 and \
               isinstance(self.data, dpkt.Packet) and self.data.sum == 0:
                # Set zeroed TCP and UDP checksums for non-fragments.
                p = str(self.data)
                s = dpkt.struct.pack('>4s4sxBH', self.src, self.dst,
                                     self.p, len(p))
#-                s = dpkt.in_cksum_add(0, s)
#-                s = dpkt.in_cksum_add(s, p)
#-                self.data.sum = dpkt.in_cksum_done(s)
                #  Get the checksum of concatenated pseudoheader+TCP packet
                self.data.sum = dpkt.in_cksum(s+p)
                if self.p == 17 and self.data.sum == 0:
                    self.data.sum = 0xffff  # RFC 768
                # XXX - skip transports which don't need the pseudoheader
        return self.pack_hdr() + self.opts + str(self.data)

