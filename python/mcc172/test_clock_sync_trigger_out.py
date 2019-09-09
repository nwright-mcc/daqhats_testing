#!/usr/bin/env python
import time
import sys
from daqhats import mcc172, SourceType, AliasMode
import RPi.GPIO as GPIO

CLOCK_PIN = 19
SYNC_PIN = 6
TRIGGER_PIN = 5

def cleanup_and_exit(board, code):
    GPIO.setup(CLOCK_PIN, GPIO.IN)
    GPIO.setup(TRIGGER_PIN, GPIO.IN)
    GPIO.setup(SYNC_PIN, GPIO.IN)
    board.a_in_clock_config_write(SourceType.LOCAL, AliasMode.NORMAL, 51200)
    sys.exit(code)
    
def main():
    # Set the device to clock/trigger slave mode, write known values on the Pi
    # GPIO, then read the signal values from the micro to verify them.

    board = mcc172(0)
    board.a_in_clock_config_write(SourceType.SLAVE, AliasMode.NORMAL, 51200)
    board.trigger_config(SourceType.SLAVE, 0)

    # Set the Pi GPIO pins as outputs
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(CLOCK_PIN, GPIO.OUT)
    GPIO.setup(TRIGGER_PIN, GPIO.OUT)
    GPIO.setup(SYNC_PIN, GPIO.OUT)

    # Set clock, sync, trigger low
    GPIO.output(CLOCK_PIN, 0)
    GPIO.output(TRIGGER_PIN, 0)
    GPIO.output(SYNC_PIN, 0)
    time.sleep(0.01)
    # Read the test signals from the micro
    values = board.test_signals_read()
    if values.clock != 0:
        print "Clock did not read 0."
        cleanup_and_exit(board, 1)
    if values.sync != 0:
        print "Sync did not read 0."
        cleanup_and_exit(board, 1)
    if values.trigger != 0:
        print "Trigger did not read 0."
        cleanup_and_exit(board, 1)

    # Set clock, sync, trigger high
    GPIO.output(CLOCK_PIN, 1)
    GPIO.output(TRIGGER_PIN, 1)
    GPIO.output(SYNC_PIN, 1)
    time.sleep(0.01)
    # Read the test signals from the micro
    values = board.test_signals_read()
    if values.clock != 1:
        print "Clock did not read 1."
        cleanup_and_exit(board, 1)
    if values.sync != 1:
        print "Sync did not read 1."
        cleanup_and_exit(board, 1)
    if values.trigger != 1:
        print "Trigger did not read 1."
        cleanup_and_exit(board, 1)

    print "Test passed."
    cleanup_and_exit(board, 0)

if __name__ == '__main__':
    main()
