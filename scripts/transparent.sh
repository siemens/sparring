#!/bin/sh
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
#
# This script is part of sparring.
# It can be used to set up network and operating system parameters needed for
# analysis of traffic with sparring in TRANSPARENT mode.
# 
# Assumptions made:
# 1) Analysis takes place in virtualised guests
# 2) The maximum number of guests is known. $TAPS will not be set lower
# 3) The physical interface will shortly be unavailable during invocation of
# this script for acquiring a DHCP-assigned IP address
# 4) Note that 3) implies that the physical host gets configured by DHCP!
# 5) Guests should be configured with static IP addresses as this allows for
# better correlating them during the analysis (and chosing the right -a
# parameter of sparring)
# 6) host services like SSH.. should be bound to 0.0.0.0 or the _bridge's_ IP
# 7) After analysis, the physical interface is advised to reclaim a
# DHCP-assigned IP address
#
# For now, this script assumes, that an analysis of virtualised hosts is done.
# Therefore it takes care to isolate these from each other. Different
# scenarios where local traffic has to be dissected, are also supported, the
# corresponding rules in ipt_rules() have to be enabled in this case.

# The following variables can be tuned for different environments. At present
# there are no cmdline switches to set them as using local variables keeps the
# invocation of this script rather simple.
#
# physical interface used for host-external connectivity
DEV=eth0
# number of tap-devices to use, starting at tap1
TAPS=2
BRIDGE=br0

reset_net() {
  unset_nfqueue
  unset_net
}

set_nfqueue() {
  ipt_rules -A
}

unset_nfqueue() {
  ipt_rules -D
}

ipt_rules() {
for i in `seq 1 $TAPS`; do
  # if you want to analyse 'host' traffic in a non-virtualised environment,
  # enable the following two rules. You may disable th FORWARD-chain rule, too.
  #iptables $1 OUTPUT -p tcp -j NFQUEUE --queue-num $QUEUE
  #iptables $1 INPUT -p tcp -j NFQUEUE --queue-num $QUEUE

  # setup in VBox: bridged over tap0 <- eth0 -> br0
  iptables $1 FORWARD -p tcp -m physdev --physdev-is-bridged --physdev-out tap${i} -j NFQUEUE --queue-num $i
  iptables $1 FORWARD -p tcp -m physdev --physdev-is-bridged --physdev-in  tap${i} -j NFQUEUE --queue-num $i

  # if you want to analyse 'host' traffic in a non-virtualised environment,
  # enable the following two rules. You may disable th FORWARD-chain rule, too.
  #iptables $1 OUTPUT -p udp -j NFQUEUE --queue-num $QUEUE
  #iptables $1 INPUT -p udp -j NFQUEUE --queue-num $QUEUE

  # setup in VBox: bridged over tap0 <- eth0 -> br0
  iptables $1 FORWARD -p udp -m physdev --physdev-is-bridged --physdev-out tap${i} -j NFQUEUE --queue-num $i
  iptables $1 FORWARD -p udp -m physdev --physdev-is-bridged --physdev-in  tap${i} -j NFQUEUE --queue-num $i
done

  # be really strict about everything that's not TCP or UDP: DROP it.
  iptables $1 FORWARD -m physdev --physdev-is-bridged --physdev-out tap+ -j DROP
  iptables $1 FORWARD -m physdev --physdev-is-bridged --physdev-in tap+ -j DROP

  # if all VMs are bridged together with eth0 in br0, disallow traffic between
  # VMs so they are isolated from each other:
  #ebtables -F FORWARD
  if [ $1 == "-A" ]; then
    ebtables -P FORWARD DROP
  else
    ebtables -P FORWARD ACCEPT
  fi

  ebtables $1 FORWARD -i $DEV -j ACCEPT
  ebtables $1 FORWARD -o $DEV -j ACCEPT

}

setup_net() {

  brctl addbr $BRIDGE
  brctl addif $BRIDGE $DEV

  for i in `seq 1 $TAPS`; do
    ip tuntap add tap${i} mode tap
    brctl addif $BRIDGE tap${i}
  done

  ip link set up dev $DEV
  for i in `seq 1 $TAPS`; do
    ip link set up dev tap${i}
  done
  ip link set up dev $BRIDGE
  
  killall -q dhcpcd
  #ip addr replace dev $DEV 0.0.0.0
  # TODO bad: hard coded..
  ip addr del 192.168.1.100/24 dev eth0
  dhcpcd -q $BRIDGE
  
  # stop nfqueue (binding) from failing:
  # Initial settings will NOT get restored!
  sysctl -qw net.core.rmem_default=8388608
  sysctl -qw net.core.wmem_default=8388608
  sysctl -qw net.ipv4.tcp_wmem='1048576 4194304 16777216'
  sysctl -qw net.ipv4.tcp_rmem='1048576 4194304 16777216'
  
  set_nfqueue

}

unset_net() {
  dhcpcd -x $BRIDGE

  ip link set down dev $BRIDGE 
  for i in `seq 1 $TAPS`; do
    ip link set down dev tap${i}
  done
  ip link set down dev $DEV

  brctl delif $BRIDGE $DEV
  for i in `seq 1 $TAPS`; do
    brctl delif $BRIDGE tap${i}
    ip tuntap del tap${i} mode tap
  done
  brctl delbr $BRIDGE
  dhcpcd -q $DEV
}

usage() {
  echo "$0 [start|startipt|stopipt|stop|restart]"
}

case $1 in
start)
    setup_net
    ;;
startipt)
    set_nfqueue
    ;;
stopipt)
    unset_nfqueue
    ;;
stop)
    reset_net
    ;;
restart)
    reset_net
    setup_net
    ;;
  *)
    usage
    ;;
esac

