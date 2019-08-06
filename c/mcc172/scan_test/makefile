CC=gcc
CFLAGS = -I/usr/local/include
OFLAGS = -ldaqhats
TARGETS = scan_test

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

all: $(TARGETS)

scan_test: scan_test.o
	$(CC) -o $@ $^ $(OFLAGS)

.PHONY: clean

clean:
	rm -f *.o *~ $(TARGETS) *.bin
