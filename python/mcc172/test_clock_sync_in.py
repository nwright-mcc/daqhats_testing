#!/usr/bin/env python
import time
import sys
from daqhats import mcc172, SourceType, AliasMode
import RPi.GPIO as GPIO

# Set the Pi GPIO pins as inputs
CLOCK_PIN = 19
SYNC_PIN = 6
TRIGGER_PIN = 5

GPIO.setmode(GPIO.BCM)
GPIO.setup(CLOCK_PIN, GPIO.IN)
GPIO.setup(TRIGGER_PIN, GPIO.IN)
GPIO.setup(SYNC_PIN, GPIO.IN)

def cleanup_and_exit(board, code):
    board.test_signals_write(0, 0, 0)
    board.a_in_clock_config_write(SourceType.LOCAL, AliasMode.NORMAL, 51200)
    sys.exit(code)
    
def main():
    # Set the device to clock master mode, put it into test mode, set the clock
    # signal to known values, then read the Pi GPIO for shared clock to verify the
    # value.

    board = mcc172(0)
    board.a_in_clock_config_write(SourceType.MASTER, AliasMode.NORMAL, 51200)

    # Set clock, sync low
    board.test_signals_write(1, 0, 0)
    time.sleep(0.01)
    # Read the Pi GPIO
    if GPIO.input(CLOCK_PIN) != 0:
        print "Clock did not go to 0."
        cleanup_and_exit(board, 1)
    if GPIO.input(SYNC_PIN) != 0:
        print "Sync did not go to 0."
        cleanup_and_exit(board, 1)

    # Set clock, sync high
    board.test_signals_write(1, 1, 1)
    time.sleep(0.01)
    # Read the Pi GPIO
    if GPIO.input(CLOCK_PIN) != 1:
        print "Clock did not go to 1."
        cleanup_and_exit(board, 1)
    if GPIO.input(SYNC_PIN) != 1:
        print "Sync did not go to 1."
        cleanup_and_exit(board, 1)

    print "Test passed."
    cleanup_and_exit(board, 0)

if __name__ == '__main__':
    main()
