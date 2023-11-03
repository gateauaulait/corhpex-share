CC=gcc
LDFLAGS=-lhwloc
CFLAGS=-O3
EXEC=bindings-gen

all: $(EXEC)

$(EXEC): main.c
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

clean:
	rm -rf $(EXEC)
