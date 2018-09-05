#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, sys
from optparse import OptionParser
try:
    from scapy.all import *
except:
    print("\nDependency problem, please install scapy.\n")
    exit(0)

W = '\033[0m'   # white
R = '\033[31m'  # red
G = '\033[32m'  # green

def print_ok():
    print(W+"["+G+"ok"+W+"]")

def print_err():
    print(W+"["+R+"error"+W+"]")


def run_command(*args, **kwargs):
	"Run a command and return stdout or stderr"
	print("Running command: ", end = "")
	print(' '.join(args)+" ... ", end=" ")
	try:
		res = subprocess.check_output(args, stderr=subprocess.STDOUT)
	except subprocess.CalledProcessError:
		print_err()
		return None
	print_ok()
	return res


def parse_arp_entry(entry):
	try:
		entry = entry.decode("utf-8")
		ip = (entry.split('('))[1].split(')')[0]
		mac = (entry.split('at '))[1].split(' on')[0]
		return (ip, mac)
	except:
		return None

def create_mask_from_cidr_prefix(prefix):
    "Return a network mask from a CIDR prefix"

    mask = []
    b = [128, 64, 32, 16, 8, 4, 2, 1]
    # how many times all bits are set to 1
    try:
        it = int( int(prefix) / 8)
    except:
        return None
    # the rest of the bits set to 1
    md = prefix % 8
    for i in range(it):
        mask.append( sum(b) )

    if md != 0:
        mask.append( sum(b[:md]) )

    # pad the mask
    while len(mask) < 4:
        mask.append(0)

    return mask

def in_same_net(ip1, ip2, cidr_prefix):
    "Check if ip2 address is in the same network as ip1"

    mask = create_mask_from_cidr_prefix(cidr_prefix)
    if mask is None:
        return None

    try:
        sub_ip1 = ip1.split('.')
        sub_ip2 = ip2.split('.')
    except:
        return None

    # function that perform a binary AND on two items
    et = lambda x,y: int(x) & int(y)

    # apply the 'et' function using the ip address and the mask
    ip1_net = list(map( et, sub_ip1, mask ))
    ip2_net = list(map( et, sub_ip2, mask ))
    if ip1_net == ip2_net:
        return True
    "Check for broadcast address"


def is_ipv4(ip):
    "Return True if it's an ipv4 address"
    if '.' in ip:
        return True

    return False

def neigh(iface, my_ip):
    "Return a list of tuples (ipv4, mac@) of neighbor machines"
    neighbor = []
    ip_mask = my_ip.split('/')
    result = run_command("ip", "neigh")
    if not result:
        return None

    lines = result.split(b'\n')
    # get only "reachable" neighors of the selected interface
    lines = [line for line in lines if iface in str(line)\
                                        if "REACHABLE" in str(line)]

    for line in lines:
        ip = line.split(b' ')[0].decode("utf-8")
        if is_ipv4(ip):
            if in_same_net(ip_mask[0], ip, int(ip_mask[1])):
                neighbor.append( ip )

    print(neighbor)
    return neighbor

def check_for_inet(iter):
	"Return True if their is an ipv4 address in the iterable"
	for line in iter:
		addr_type = line.split(" ")[0]
		if addr_type == 'inet':
			return True
	print("Interface doesn't have an IPv4 assigned")
	return False


def get_my_ip_mac(iface):
    "Return tuple (ipv4, mac@) if exists, None otherwise"
    res = run_command("ip", "a", "show", "dev", iface)
    if not res:
        return None

    res = res.decode("utf-8").split('\n\t')
    if not check_for_inet(res):
        return None

    ip, mac = "", ""
    for r in res:
        entry = r.split(" ")
        if entry[0] == 'inet':
            ip_mask = entry[1]
        elif entry[0] == 'ether':
            mac = entry[1]

    return (ip_mask, mac)


def build_arp_packet( iface, my_ip_mac, neighbors ):

    if len( neighbors ) <= 1:
        print("There are no enough neighbors to be sure")
    answer = False
    # set verbosity to None
    # conf.verb = 0
    ipsrc = '.'.join(my_ip_mac[0].split(".")[:-1] )+'.12'
    for ip, mac in neighbors:
        eth = Ether( src=my_ip_mac[1], dst=mac )
        arp = ARP( pdst=my_ip_mac[0], psrc=my_ip_mac[0] )
        pckt = eth/arp
        try:
            ans , unans = srp( pckt , timeout = 2 )
            #ans = ans.summary(lambda s,r: r.sprintf("%Ether.src% %ARP.psrc%") )
            print( ans.summary(lambda s,r: r.sprintf("%Ether.src% %ARP.psrc%") ) )
            """if ans:
                answer = True
                print( "Answer from "+ ip +" : \n\t" + ans )"""
        except:
            pass
    """if not answer:
        print("No reply has been received.")"""
    return 0


def main( ):

    option_parser = OptionParser()
    option_parser.add_option("-i", "--intf", dest="iface",
                      help="network interface to use")

    (options, args) = option_parser.parse_args()
    if options.iface is None:
        print("Missing argument.")
        print("Please use -h for more information.")
        print("\t"+sys.argv[0]+ " -h")
        exit("\n")

    neighbor = []
    my_ip_mac = []
    print("\n")
    my_ip_mac = get_my_ip_mac( options.iface )
    if not my_ip_mac:
        exit(0)

    print("My ip is: "+my_ip_mac[0])
    print("My mac address is: "+my_ip_mac[1])

    neighbor = neigh( options.iface, my_ip_mac[0] )
    if not neighbor:
        print("No neighbor found")
        exit(0)
    #build_arp_packet( options.iface, my_ip_mac, neighbor )


if __name__ == '__main__':
	main( )
