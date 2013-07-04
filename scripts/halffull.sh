#!/bin/sh
# Copyright (C) 2012-2013 sparring Developers.
# This file is part of sparring - http://github.com/thomaspenteker/sparring
# See the file 'docs/LICENSE' for copying permission.
#
# BEWARE THIS IS SEMI-TESTED CODE AND IT WON'T EVEN WORK FOR UDP SO DON'T
# EVEN BOTHER TRYING TO USE THIS FOR UDP IN HALF OR FULL MODE.

DEV=eth0
TAPS=1
BRIDGE=br0

bridge() {
  if [ $1 == "-A" ]; then
    brctl addbr $BRIDGE
    brctl addif $BRIDGE $DEV
    for i in `seq 1 $TAPS`; do
      brctl addif $BRIDGE tap${i}
    done
  else
    ip link set down $BRIDGE
    brctl delbr $BRIDGE
  fi
}

tables() {
  if [ $1 == "-A" ]; then
    ip route add local 0.0.0.0/0 dev lo table 100
    ip rule add fwmark 1 lookup 100
  else
    ip route delete table 100
    ip rule delete fwmark 1 lookup 100
    # ?
    ip route delete default via 127.0.0.1
  fi
}

redirect() {

  if [ $1 == "-A" ]; then
    iptables -t mangle -N DIVERT
  fi
  #
  # TCP
  #
  iptables -t mangle $1 DIVERT -p tcp -j MARK --set-mark 1
  iptables -t mangle $1 DIVERT -p tcp -j ACCEPT
  for i in `seq 1 $TAPS`; do
    iptables -t mangle $1 PREROUTING -p tcp -i tap${i} -m socket -j DIVERT
    iptables -t mangle $1 PREROUTING -p tcp -i tap${i} -j TPROXY --tproxy-mark 0x1/0x1 --on-port 500${i} --on-ip 127.0.0.1
    # make all bridged TCP packets subject to packet filtering
    ebtables -t broute $1 BROUTING -p ip --ip-protocol tcp -j redirect --redirect-target DROP
  done

  #
  # UDP
  #
  for i in `seq 1 $TAPS`; do
    iptables -t mangle $1 PREROUTING -p udp -i tap${i} -j TPROXY --tproxy-mark 0x1/0x1 --on-port 500${i} --on-ip 127.0.0.1
    # make all bridged UDP packets subject to packet filtering
    ebtables -t broute $1 BROUTING -p ip --ip-protocol udp -j redirect --redirect-target DROP
  done

  # work around some _awkward_ bug:
  iptables -t mangle -I PREROUTING -p icmp -d 11.222.33.44 -j DROP
  iptables -t mangle -D PREROUTING -p icmp -d 11.222.33.44 -j DROP

  if [ $1 == "-D" ]; then
    iptables -t mangle -X DIVERT
  fi

}

set_net() {

  #ip route add default via 127.0.0.1
  ip link set down dev $DEV
  ip addr change dev $DEV 0.0.0.0
  
  for i in `seq 1 $TAPS`; do
    ip tuntap add tap${i} mode tap
    ip addr change dev tap${i} 0.0.0.0
  done
  
  bridge -A
  
  ip link set up dev $DEV
  for i in `seq 1 $TAPS`; do
    ip link set up dev tap${i}
  done
  ip link set up dev $BRIDGE
  
  killall dhcpcd
  sleep 2s
  dhcpcd $BRIDGE

}

reset_net() {
  redirect -D
  tables -D
  bridge -D
  for i in `seq 1 $TAPS`; do
    ip tuntap del tap${i} mode tap
  done
  ip link set up dev $DEV
}

usage() {
  echo "$0 [start|stop|restart]"
}

case $1 in
start)
    set_net
    tables -A
    redirect -A
    ;;
startipt)
    redirect -A
    ;;
stopipt)
    redirect -D
    ;;
stop)
    reset_net
    tables -D
    redirect -D
    ;;
restart)
    reset_net
    set_net
    ;;
  *)
    usage
    ;;
esac

