#!/usr/bin/env python3

import sys
import hid # pip install hidapi
from struct import pack, unpack
import csv

VENDOR_ID = 0x2f68 
PRODUCT_ID = 0x0082 # DURGOD Taurus K320:
TIMEOUT = 200

KEEPALIVE   = b"\x00\x03\x07\xE3"
RESET       = b"\x00\x03\x05\x80\x04\xff".ljust(64, b"\x00")

N = 8
WRITE       = b"\x00\x03\x05\x81\x0f\x00\x00"
WRITE_RESP  = b"\x83\x05\x81\x0f\x00\x00\x00h"

SAVE        = b"\x00\x03\x05\x82"
DISCONNECT  = b"\x00\x03\x19\x88" # Disconnect? is sent on application exit 

KEYNAMES = dict()
KEYNAMES[0x28] = 'Enter'
KEYNAMES[0x2C] = 'Space'
KEYNAMES[0x49] = 'Insert'
KEYNAMES[0xE0] = 'LCtrl'
KEYNAMES[0xE1] = 'LShift'
KEYNAMES[0xE2] = 'LAlt'
KEYNAMES[0xE3] = 'LWindows'
KEYNAMES[0xE4] = 'RCtrl'
KEYNAMES[0xE5] = 'RShift'
KEYNAMES[0xE6] = 'RAlt'
KEYNAMES[0xE7] = 'RWindows'

KEYNAMES[0x2B] = 'Tab'
KEYNAMES[0x39] = 'CapsLock'
KEYNAMES[0x2a] = 'Backspace'
KEYNAMES[0x4a] = 'Pos1'
KEYNAMES[0x4b] = 'PageUp'
KEYNAMES[0x4c] = 'Delete'
KEYNAMES[0x4d] = 'End'
KEYNAMES[0x4e] = 'PageDown'
KEYNAMES[0x50] = 'Left'
KEYNAMES[0x51] = 'Down'
KEYNAMES[0x52] = 'Up'
KEYNAMES[0x4f] = 'Right'
KEYNAMES[0x46] = 'Print'
KEYNAMES[0x47] = 'Roll'
KEYNAMES[0x48] = 'Roll'

# f1-f12
for i in range(0,12):
    KEYNAMES[0x3A+i] = "f%d" % (i+1)

# 0-9
for i in range(0,9):
    KEYNAMES[0x1E+i] = "%d" % (i+1)
# a-z
for c in range(0,26):
    KEYNAMES[4+c] = chr(ord('a')+c)

def connect():
    device_info = next(device for device in hid.enumerate() if device['vendor_id'] == VENDOR_ID and device['product_id'] == PRODUCT_ID and device['interface_number'] == 2 )

    device = hid.device()
    device.open_path(device_info['path'])
    return device


def send(device, data):
    if device.write(data.ljust(64, b"\x00")) < 0: 
        raise "Write failed"

    resp = device.read(64, timeout_ms=500)
    print("<-", end="")
    resp = bytearray(resp).rstrip(b'\x00')
    print(resp)
    return resp



def reprogram(keymap):
    device = connect()

    send(device, KEEPALIVE)
    send(device, RESET)

    for i, d in enumerate(keymap):
        resp = send(device, b''.join([WRITE, pack('b', i), d]))
        if resp != bytearray(WRITE_RESP):
            raise Exception(f"Bad response f{resp}")

    send(device, SAVE)
    send(device, KEEPALIVE)
    send(device, DISCONNECT) 
    device.close()


def print_keymap(keymap):
    ROW_LENGTH = 21

    keymap_parsed = []
    for arg in keymap:
        row = arg[0:N*4]
        n = min(N, int(len(arg)/4))
        keymap_parsed += unpack('>'  + n*'I', arg)
    for i, c in enumerate(keymap_parsed):
        if (i % ROW_LENGTH) == 0:
            print("")
        if c in KEYNAMES:
            print("%10s" % KEYNAMES[c], end='\t')
        else:
            print("%10xh" % c, end='\t')

    print("")

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def read_keymap(path):
    keymap = []
    with open(path) as f:
        for lineNr, line in enumerate(csv.reader(f, delimiter='\t')):
            if line[-1] == '':
                # ignore tailing tabs (useful when reformatting)
                line = line[0:-1]
            for keyname in line:
                keyname = keyname.strip()
                keycode = next((name for name, value in KEYNAMES.items() if value == keyname), None)
                if not keycode is None:
                    keymap.append(keycode)
                elif keyname.endswith('h'):
                    keymap.append(int(keyname[:-1], 16))
                else:
                    raise Exception(f"[{lineNr}]: Invalid key '{keyname}'")
    return keymap


def format_reprogram_command(data):
    r = b''
    for key in data:
       r += pack('>I', key)
    return r

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} keymap")
        sys.exit(-1)

    keymap_file = sys.argv[1]
    loaded_keymap = read_keymap(keymap_file)
    assert len(loaded_keymap) == 126, "Keymap length is not what was expected, invalid file?"
   
    commands = [format_reprogram_command(cmd) for cmd in chunks(loaded_keymap, 8)]
    extra = b"\x78\x56\x34\x12"
    commands[-1] = commands[-1][0:29] + extra
    
    print_keymap(commands)
    reprogram(commands)
