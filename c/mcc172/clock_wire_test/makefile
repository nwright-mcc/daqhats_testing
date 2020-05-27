#Set all object files
OBJ = finite_scan.o

#Set all dependant header files
#DEPS = continuous_scan.h

#Set libraries
LIBS = -ldaqhats

#Set compiler flags
CFLAGS = -Wall -I/usr/local/include -g

#Set the compiler ( gcc for C or g++ for C++ )
CC = gcc

#Set the filename extensiton (e.g. .c or .cpp )
EXTENSION = .c

#Compile each object file
%.o: %$(EXTENSION) $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

#Combine them into the output file
finite_scan: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) $(LIBS)

#Cleanup
.PHONY: clean

clean:
	rm -f *.o *~ core *~ 
