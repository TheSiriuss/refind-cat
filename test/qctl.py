#!/usr/bin/env python3
"""Tiny QEMU HMP client: qctl.py <qwork-dir|socket> <cmd> [<cmd> ...]   ('sleep:N' waits N seconds; info*/quit output is printed)."""
import os, socket, sys, time
sock = sys.argv[1]
if os.path.isdir(sock): sock = open(sock + '/mon.path').read().strip()     # a QWORK directory
s = socket.socket(socket.AF_UNIX); s.connect(sock); s.settimeout(2)
def rd():
    out = b''
    try:
        while True:
            d = s.recv(65536)
            if not d: break
            out += d
    except socket.timeout: pass
    return out.decode(errors='replace')
rd()
for c in sys.argv[2:]:
    if c.startswith('sleep:'): time.sleep(float(c[6:])); continue
    s.sendall(c.encode() + b'\n'); r = rd()
    if c.startswith(('info', 'quit')): print(r.strip())
