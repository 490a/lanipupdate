#!/usr/bin/python
#lanipupdate.py
#Daniel Lee
#6.18.2012
#Updates a WGR614 NetGear router's proxy port forwarding to the system's current local ip address.
#Useful because local ip address can change with any router reset or settings change.
#Currently only works for updating a webserver (i.e. only updates the HTTP port, but can be easily
#updated to be more general.
#Intended to be run as a cron job

import fcntl
import array
import struct
import socket
import platform
import time
import requests
import sys
from bs4 import BeautifulSoup

from requests.auth import HTTPBasicAuth

# global constants.  If you don't like 'em here,
# move 'em inside the function definition.
SIOCGIFCONF = 0x8912
MAXBYTES = 8096

def localifs():
    """
    Used to get a list of the up interfaces and associated IP addresses
    on this machine (linux only).

    Returns:
        List of interface tuples.  Each tuple consists of
        (interface name, interface IP)
    from Samuel Nelson's post on
    http://code.activestate.com/recipes/439093-get-names-of-all-up-network-interfaces-linux-only/
    """
    global SIOCGIFCONF
    global MAXBYTES

    arch = platform.architecture()[0]

    # I really don't know what to call these right now
    var1 = -1
    var2 = -1
    if arch == '32bit':
        var1 = 32
        var2 = 32
    elif arch == '64bit':
        var1 = 16
        var2 = 40
    else:
        raise OSError("Unknown architecture: %s" % arch)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * MAXBYTES)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        sock.fileno(),
        SIOCGIFCONF,
        struct.pack('iL', MAXBYTES, names.buffer_info()[0])
        ))[0]

    namestr = names.tostring()
    return [(namestr[i:i+var1].split('\0', 1)[0], socket.inet_ntoa(namestr[i+20:i+24])) \
            for i in xrange(0, outbytes, var2)]


def get_ip_address(ifname):
    """
    from Paul Cannon's post on:
    http://code.activestate.com/recipes/439094-get-the-ip-address-associated-with-a-network-inter/
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])



data = {
'server_ip1':'192',
'server_ip2':'168',
'server_ip3':'1',
'server_ip4':'2',
'apply':'Apply',
'action':'edit_apply',
'oldService':'HTTP',
'oldType':'TCP',
'newType':'TCP',
'oldSport':'80',
'oldEport':'80',
'oldIP':'192.168.1.2',
'newIP':'192.168.1.2',
'lanIP':'192.168.1.1',
'entryData':'HTTP;1;80;80;192.168.1.2;2',
'predefined':'predefined'
}

header = {
'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
'Accept-Charset':'windows-949,utf-8;q=0.7,*;q=0.3',
'Accept-Encoding':'gzip,deflate,sdch',
'Accept-Language':'en,ko;q=0.8,en-US;q=0.6',
'Authorization':'Basic YWRtaW46bjMwbTg5M20qJg==',
'Cache-Control':'max-age=0',
'Connection':'keep-alive',
'Host':'192.168.1.1',
'Origin':'http://192.168.1.1',
'Referer':'http://192.168.1.1/pforward.cgi',
'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.56 Safari/536.5',
}

def logout():
    a = requests.get('http://192.168.1.1/LGO_logout.htm', auth=HTTPBasicAuth('admin', 'n30m893m*&'), headers=header)
    if a.ok:
        print "router logged out"
    else:
        print "router logout failed"


def get_old_IP(localnetworkip):
    a = requests.get('http://192.168.1.1/FW_forward.htm', auth=HTTPBasicAuth('admin', 'n30m893m*&'), headers=header)
    attempts = 0
    while(not a.ok and attempts < 15):
        print "finding old IP failed; attempting again.."
        a = requests.get('http://192.168.1.1/FW_forward.htm', auth=HTTPBasicAuth('admin', 'n30m893m*&'), headers=header)
        time.sleep(1)
        attempts += 1
    soup = BeautifulSoup(a.text)
    try: 
        values = soup.find_all('input', {"name":"entryData"})[0]['value'].split('@')
        for val in values:
            if "HTTP" in val:
                oldIP = val.split(';')[1]
    except IndexError:
        print "couldn't find oldIP in the following:"
        print a.text

    if oldIP:
        if oldIP == localnetworkip:
            print "current IP is same as old IP, no need to update."
            logout()
            sys.exit()
        return oldIP
    else:
        print "oldIP doesn't exist, router update failed"
        logout()
        sys.exit()

def post_update(data):
    a = requests.post('http://192.168.1.1/pforward.cgi', auth=HTTPBasicAuth('admin','n30m893m*&'), data=data, headers=header)
    if a.ok:
        print "router port forwarding updated to local ip of ", localnetworkip
    else:
        print "update attempt failed, post retrieved:", a.text


ifs = localifs()[1][0]
localnetworkip = get_ip_address(ifs)

data['server_ip4'] = localnetworkip.split('.')[3]
data['oldIP'] = get_old_IP(localnetworkip)
data['newIP'] = localnetworkip
newEntryData = 'HTTP%3B1%3B80%3B' + localnetworkip + '%3B2'
data['entryData'] = newEntryData


post_update(data)
logout()
