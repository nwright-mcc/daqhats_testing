#!/usr/bin/env python
import socket
import errno
import struct
#import os
import signal
import time
import subprocess
from threading import Thread, Event
from SocketServer import ThreadingMixIn
from daqhats import mcc172, OptionFlags
import binascii

class ClientThread(Thread):
 
    def __init__(self, conn, ip, port):
        Thread.__init__(self)
        self._stop_event = Event()
        self.ip = ip
        self.port = port
        self.conn = conn
        self.hat = mcc172(3)
        print "[+] New thread started for "+ip+":"+str(port)
 
    def stop(self):
        self._stop_event.set()
        
    def run(self):
        scanning = False
        
        while not self._stop_event.is_set():
            try:
                data = self.conn.recv(2048)
            except socket.timeout, e:
                err = e.args[0]
                if err == 'timed out':
                    time.sleep(0.1)
                    continue
                else:
                    break
            except socket.error, e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    time.sleep(0.1)
                    continue
                else:
                    break
            else:
                if not data:
                    break

                command = struct.unpack('B', data[0:1])
                #print binascii.hexlify(data)
                
                # first byte is the command code
                if command[0] == 0x00:
                    if len(data) >= 3:
                        (channel, value) = struct.unpack_from('BB', data, 1)
                        print "IEPE power {0} {1}".format(channel, value)
                        self.hat.iepe_config_write(channel, value)
                        self.conn.send(struct.pack('B', 1))
                elif command[0] == 0x01:
                    if len(data) >= 10:
                        values = struct.unpack_from('>Bd', data, 1)
                        clock_source = values[0]
                        clock_frequency = values[1]
                        print "Config clock {0} {1:.1f}".format(clock_source, clock_frequency)
                        self.hat.a_in_clock_config_write(clock_source, clock_frequency)
                        synced = False
                        while not synced:
                            time.sleep(0.01)
                            result = self.hat.a_in_clock_config_read()
                            synced = result.synchronized
                        packed_data = struct.pack('>d', result.sample_rate_per_channel)
                        self.conn.send(packed_data)
                elif command[0] == 0x02:
                    if len(data) >= 6:
                        values = struct.unpack_from('>Bl', data, 1)
                        channel = values[0]
                        samples = values[1]
                        print "Read data {0} {1}".format(channel, samples)
                        if channel == 0:
                            channel_mask = 0x01
                        else:
                            channel_mask = 0x02
                        self.hat.a_in_scan_start(channel_mask, samples, 0)
                        samples_read = 0
                        scan_data = []
                        while (samples_read < samples):
                            time.sleep(0.1)
                            scan_tuple = self.hat.a_in_scan_read(-1, 0)
                            if scan_tuple.hardware_overrun or scan_tuple.buffer_overrun:
                                break
                            scan_data.extend(scan_tuple.data)
                            samples_read += len(scan_tuple.data)
                        
                        self.hat.a_in_scan_stop()
                        
                        flags = (int(scan_tuple.running) * 8 + 
                            int(scan_tuple.triggered) * 4 +
                            int(scan_tuple.buffer_overrun) * 2 +
                            int(scan_tuple.hardware_overrun))
                        if len(scan_data) > 0:
                            pack_string = '>Bl{}d'.format(len(scan_data))
                            packed_data = struct.pack(pack_string, flags, len(scan_data), *scan_data)
                        else:
                            packed_data = struct.pack('Bl', flags, 0)
                        self.conn.send(packed_data)
                        
                        self.hat.a_in_scan_cleanup()
                        
        print("[-] Thread exit")
 


def signal_handler(sig, frame):
    global running
    running = False
    
running = True
signal.signal(signal.SIGINT, signal_handler)
    
TCP_IP = '0.0.0.0'
TCP_PORT = 62
BUFFER_SIZE = 20  # Normally 1024, but we want fast response
 
tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcpsock.setblocking(0)
tcpsock.bind((TCP_IP, TCP_PORT))
threads = []

p = subprocess.Popen(['hostname', '-I'], stdout=subprocess.PIPE)
my_ip = p.communicate()[0]

print "Server IP address is {}".format(my_ip)
print "Waiting for incoming connections..."
tcpsock.listen(4)
while running:
    try:
        (conn, (ip,port)) = tcpsock.accept()
    except socket.error, e:
        err = e.args[0]
        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
            time.sleep(1)
            continue
        else:
            break
    except socket.timeout, e:
        err = e.args[0]
        if err == 'timed out':
            time.sleep(1)
            continue
        else:
            break
    else:
        newthread = ClientThread(conn, ip, port)
        newthread.start()
        threads.append(newthread)
        print "Waiting for incoming connections..."
        tcpsock.listen(4)
 
for t in threads:
    t.stop()
    t.join()
    
