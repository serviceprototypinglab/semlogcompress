# Wraps valgrind's massif tool to inquire about maximum memory usage of a command line invocation
# Sums up memory usage across subprocesses

import sys
import glob
import os

if len(sys.argv) < 2:
    print("Call: massifmem.py cmd...", file=sys.stderr)
    exit(1)

fns = glob.glob("massif.out.*")
for fn in fns:
    os.remove(fn)

os.system("valgrind --tool=massif " + " ".join(sys.argv[1:]))

fns = glob.glob("massif.out.*")
print(fns)

totalmem = 0
for fn in fns:
    maxmem = 0
    f = open(fn)
    for line in f:
        if line.startswith("mem_heap_B="):
            mem = int(line.strip().split("=")[1])
            #print(mem)
            if mem > maxmem:
                maxmem = mem
    print("max mem in process", maxmem, "bytes /", round(maxmem / 1024), "kB")
    totalmem += maxmem
print("total mam", totalmem, "bytes /", round(totalmem / 1024), "kB")
