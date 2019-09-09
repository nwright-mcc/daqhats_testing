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
    board.trigger_config(SourceType.LOCAL, 0)
    sys.exit(code)
    
def main():
    # Set the device to trigger master mode, prompt the user to apply known
    # trigger values, then read the Pi GPIO for shared trigger to verify the
    # values.

    board = mcc172(0)
    board.trigger_config(SourceType.MASTER, 0)

    # Set trigger low
    raw_input("Apply 0 to the trigger input then hit Enter.")
    # Read the Pi GPIO
    if GPIO.input(TRIGGER_PIN) != 0:
        print "Trigger did not go to 0."
        cleanup_and_exit(board, 1)

    # Set trigger high
    raw_input("Apply 1 to the trigger input then hit Enter.")
    # Read the Pi GPIO
    if GPIO.input(TRIGGER_PIN) != 1:
        print "Trigger did not go to 1."
        cleanup_and_exit(board, 1)

    print "Test passed."
    cleanup_and_exit(board, 0)

if __name__ == '__main__':
    main()
