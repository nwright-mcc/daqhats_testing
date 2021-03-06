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
from daqhats import mcc172, mcc134, OptionFlags
import binascii
from sensor import SHT20

class ClientThread(Thread):

    def __init__(self, conn, ip, port):
        Thread.__init__(self)
        self._stop_event = Event()
        self.ip = ip
        self.port = port
        self.conn = conn
        self.hat = mcc172(0)
	try:
            self.temp = mcc134(1)
        except:
            self.temp = None

        try:
            self.sht20 = SHT20(1, 0x40)
        except:
            self.sht20 = None

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
                        values = struct.unpack_from('>BBd', data, 1)
                        clock_source = values[0]
                        clock_frequency = values[2]
                        print "Config clock {0} {1:.1f}".format(clock_source, clock_frequency)
                        self.hat.a_in_clock_config_write(clock_source, clock_frequency)
                        synced = False
                        while not synced:
                            time.sleep(0.01)
                            result = self.hat.a_in_clock_config_read()
                            synced = result.synchronized
                        print "Set to {:.1f}".format(result.sample_rate_per_channel)
                        packed_data = struct.pack('>d', result.sample_rate_per_channel)
                        self.conn.send(packed_data)
                elif command[0] == 0x02:
                    if len(data) >= 6:
                        values = struct.unpack_from('>BlB', data, 1)
                        channel = values[0]
                        samples = values[1]
                        options = values[2]
                        print "Read data {0} {1} {2}".format(channel, samples, options)
                        if channel == 0:
                            channel_mask = 0x01
                        else:
                            channel_mask = 0x02
                        self.hat.a_in_scan_start(channel_mask, samples, options)
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
                elif command[0] == 0x03:
                    if len(data) >= 5:
                        values = struct.unpack_from('>lB', data, 1)
                        samples = values[0]
                        options = values[1]
                        print "Read data both {0} {1}".format(samples, options)
                        channel_mask = 0x03
                        self.hat.a_in_scan_start(channel_mask, samples, options)
                        samples_read = 0
                        scan_data = []
                        while (samples_read < 2*samples):
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
                elif command[0] == 0x04:
                    # read temperature from 134
                    if self.temp:
                        value = self.temp.cjc_read(0)
                        print "Read temperature {:.2f}".format(value)
                    else:
                        value = 25.0
                    packed_data = struct.pack(">d", value)
                    self.conn.send(packed_data)
                elif command[0] == 0x05:
                    # read temperature, RH from SHT20
                    if self.sht20:
                        h, t = self.sht20.all()
                        print "Read temp & RH {0:.2f} {1:.1f}".format(h.RH, t.C)
                        packed_data = struct.pack(">dd", h.RH, t.C)
                    else:
                        packed_data = struct.pack(">dd", 0, 25)
                    self.conn.send(packed_data)
                else:
                    print "Bad command {}".format(command[0])

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

