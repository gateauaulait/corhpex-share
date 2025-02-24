CC=gcc
LDFLAGS=-lhwloc
CFLAGS=-O3
EXEC=bindings-gen

all: check-deps $(EXEC)

# checking if libhwloc-dev is installed
check-deps:
	dpkg -s libhwloc-dev >/dev/null 2>&1 || sudo apt update && sudo apt install -y libhwloc-dev

$(EXEC): main.c
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

clean:
	rm -rf $(EXEC)
