#!/usr/bin/env python
import socket
import errno
import struct
#import os
import signal
import time
from datetime import date
import json
import io
from subprocess import Popen, PIPE
from threading import Thread, Event
from SocketServer import ThreadingMixIn
from daqhats import mcc128, OptionFlags
import binascii

CAL_DIR="/home/pi/daqhats_calibrate"
ADDRESS=1

class ClientThread(Thread):

    def __init__(self, conn, ip, port):
        Thread.__init__(self)
        self._stop_event = Event()
        self.ip = ip
        self.port = port
        self.conn = conn
        self.hat = mcc128(ADDRESS)
        self.temp = None

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
                    if len(data) >= 2:
                        (channel, options) = struct.unpack_from('BB', data, 1)
                        value = self.hat.a_in_read(channel, options)
                        print "AIn read {0} {1} {2}".format(channel, options, value)
                        packed_data = struct.pack('>d', value)
                        self.conn.send(packed_data)
                elif command[0] == 0x01:
                    if len(data) >= 1:
                        values = struct.unpack_from('B', data, 1)
                        print "AIn mode {0}".format(values[0])
                        self.hat.a_in_mode_write(values[0])
                        self.conn.send(struct.pack('B', 1))
                elif command[0] == 0x04:
                    if len(data) >= 1:
                        values = struct.unpack_from('B', data, 1)
                        print "AIn range {0}".format(values[0])
                        self.hat.a_in_range_write(values[0])
                        self.conn.send(struct.pack('B', 1))
                elif command[0] == 0x02:
                    if len(data) >= 6:
                        values = struct.unpack_from('>BldB', data, 1)
                        channel = values[0]
                        samples = values[1]
                        rate = values[2]
                        options = values[3]
                        print "Scan channel {0} {1} {2} {3}".format(channel, samples, rate, options)
                        if (channel < 8):
                            channel_mask = 1 << channel
                        else:
                            channel_mask = 0x01
                        self.hat.a_in_scan_start(channel_mask, samples, rate, options)
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
                        values = struct.unpack_from('>BldB', data, 1)
                        channel_mask = values[0]
                        channel_count = 0
                        temp = values[0]
                        while (temp != 0):
                            if (temp & 0x01):
                                channel_count += 1
                            temp /= 2
                        samples = values[1]
                        rate = values[2]
                        options = values[3]
                        print "Scan mask {0} {1} {2} {3}".format(channel_mask, samples, rate, options)
                        self.hat.a_in_scan_start(channel_mask, samples, rate, options)
                        samples_read = 0
                        scan_data = []
                        while (samples_read < samples*channel_count):
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
                elif command[0] == 0x05:
                    if len(data) >= 73:
                        values = struct.unpack_from('>8s8d', data, 1)
                        print "Write calibration"
                        # create xml format text file
                        serial = values[0]
                        num_ranges = 4
                        slopes = [1.0] * num_ranges
                        offsets = [0.0] * num_ranges
                        slopes[0] = values[1]
                        slopes[1] = values[2]
                        slopes[2] = values[3]
                        slopes[3] = values[4]
                        offsets[0] = values[5]
                        offsets[1] = values[6]
                        offsets[2] = values[7]
                        offsets[3] = values[8]
                        # Create calibration file
                        xdata = {}
                        xdata['serial'] = serial
                        xdata['calibration'] = {}
                        xdata['calibration']['date'] = date.today().isoformat()
                        xdata['calibration']['slopes'] = slopes
                        xdata['calibration']['offsets'] = offsets

                        hat_data = json.dumps(xdata, separators=(',', ':'), ensure_ascii=False)
                        with io.open(CAL_DIR + "/calibrate_128.txt", "w", encoding="utf8") as outfile:
                            outfile.write(unicode(hat_data))

                        self.conn.send(struct.pack('B', 1))

                        # create the EEPROM file
                        process = Popen([CAL_DIR + "/make_128_eeprom.sh"], cwd=CAL_DIR)
                        (output, err) = process.communicate()
                        exit_code = process.wait()

                        if exit_code != 0:
                            print "make_128_eeprom.sh failed"
                            self.conn.send(struct.pack('B', 0))
                        else:
                            # write the eeprom
                            process = Popen([CAL_DIR + "/program_eeprom.sh", "1"], cwd=CAL_DIR)
                            (output, err) = process.communicate()
                            exit_code = process.wait()

                            if exit_code != 0:
                                print "program_eeprom.sh failed"
                                self.conn.send(struct.pack('B', 0))
                            else:
                                # close library, read update EEPROM contents
                                process = Popen(["daqhats_read_eeproms"])
                                (output, err) = process.communicate()
                                exit_code = process.wait()
                                if exit_code != 0:
                                    print "daqhats_read_eeproms failed"
                                    self.conn.send(struct.pack('B', 0))
                                else:
                                    self.hat = None
                                    self.hat = mcc128(ADDRESS)
                                    self.conn.send(struct.pack('B', 1))

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

p = Popen(['hostname', '-I'], stdout=PIPE)
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

