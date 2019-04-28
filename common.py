import time
import signal
import socket
import inspect
import struct
import sys
import threading

def carry_around_add(x, y):
    return ((x+y) & 0xffff) + ((x + y) >> 16)

def checksum_computation(message):
    add = 0
    for i in range(0, len(message) - len(message) % 2, 2):
        message = str(message)
        w = ord(message[i]) + (ord(message[i + 1]) << 8)
        add = carry_around_add(add, w)
    return ~add & 0xffff