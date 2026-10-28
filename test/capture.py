#!/usr/bin/env python3
"""capture.py <qwork-dir|socket> <outdir> <n_frames> : loop screendump over the QEMU monitor, record wall-clock timestamps."""
import socket, sys, time, os
sock, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
if os.path.isdir(sock): sock = open(sock + '/mon.path').read().strip()
gap = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
os.makedirs(out, exist_ok=True)
s = socket.socket(socket.AF_UNIX); s.connect(sock); s.settimeout(3)
def rd():
    b = b''
    try:
        while not b.endswith(b'(qemu) '):
            d = s.recv(65536)
            if not d: break
            b += d
    except socket.timeout: pass
    return b
rd()
t0 = time.time(); ts = []
for i in range(n):
    s.sendall(f'screendump {out}/f{i:03d}.ppm\n'.encode()); rd(); ts.append(time.time() - t0); time.sleep(gap)
open(out + '/times.txt', 'w').write('\n'.join(f'{t:.4f}' for t in ts))
print('captured', n, 'frames in %.1fs' % ts[-1])
