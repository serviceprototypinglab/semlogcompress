import difflib
import sys
import os

colors = {
  "red": "\u001b[31m",
  "green": "\u001b[32m",
  "yellow": "\u001b[33m",
  "blue": "\u001b[34m",
  "magenta": "\u001b[35m",
  "cyan": "\u001b[36m",
  "white": "\u001b[37m",
  "reset": "\u001b[0m"
}

def process(fn, verbose, limit_lines):
    msgs = {}

    f = open(fn)
    i = 0
    for line in f:
        i += 1
        if limit_lines is not None and i > limit_lines:
            break

        line = line.strip()
        #print(line)
        # m - month, d - day, t - time, ip - ipv4 address, dev - device; dt - date
        if "fw" in fn:
            dt, rule, dev, port, *r = line.split()
        else:
            m, d, t, ip, dev, *r = line.split()
        r = " ".join(r)
        if verbose:
            print(r)

        clustered = False
        for msg in msgs:
            sm = difflib.SequenceMatcher(None, msg, r)
            smr = sm.ratio()
            if verbose:
                print(i, smr)
            if smr > 0.8:
                msgs[msg].append(r)
                clustered = True
                break
        if not clustered:
            msgs[r] = [r]

    return msgs

def typeget(s):
    if s.isdigit():
        return "digit"
    elif s.isalpha():
        return "alpha"
    else:
        return "mixed"

def handle(msgs, verbose):
    retlist = []

    if verbose:
        print("---")
    toh = 0
    for msg in sorted(msgs):
        types = {}

        if verbose:
            print(colors["yellow"] + msg + colors["reset"])
        alldiff = {}
        exdiff = {}
        for r in msgs[msg]:
            if verbose:
                print("*", r)
            sm = difflib.SequenceMatcher(None, msg, r)
            blocks = sm.get_matching_blocks()
            if verbose:
                print(" ", blocks)
            cblocks = ""
            lastb = None
            diff = []
            for block in blocks:
                if lastb is not None and block.size != 0:
                    cblocks += colors["red"] + r[lastb:block.b] + colors["reset"]
                    diff.append((lastb, r[lastb:block.b]))
                    exdiff[lastb] = exdiff.get(lastb, []) + [r[lastb:block.b]]
                    if not lastb in alldiff or block.b - lastb > len(alldiff[lastb]):
                        alldiff[lastb] = "*" * (block.b - lastb)
                        types[lastb] = typeget(r[lastb:block.b])
                cblocks += colors["green"] + r[block.b:block.b + block.size] + colors["reset"]
                lastb = block.b + block.size
            if verbose:
                print("→", cblocks)
                print("D", colors["magenta"] + str(diff) + colors["reset"])

        dparts = sorted(alldiff.items())
        if verbose:
            print("#", dparts)
        dblocks = ""
        lastb = 0
        oh = 0
        for dpart in dparts:
            #if lastb is not None and len(dpart[1]) != 0:
            #    dblocks += colors["red"] + r[lastb:dpart[0]] + colors["reset"]
            dblocks += colors["cyan"] + r[lastb:dpart[0]] + colors["reset"]
            dblocks += colors["red"] + dpart[1] + colors["reset"]
            lastb = dpart[0] + len(dpart[1])
            oh += len(str(dpart[0])) + len(dpart[1])
        if lastb < len(r):
            dblocks += colors["cyan"] + r[lastb:] + colors["reset"]
        print("=", dblocks)

        for j in range(len(dparts)):
            if not dparts[len(dparts) - j - 1][1]:
                continue
            offset = 0
            if verbose:
                print(" " * 3, end="")
            excerpt = []
            for dpart in dparts[:len(dparts) - j]:
                if not dpart[1]:
                    continue
                if verbose:
                    print(" " * (dpart[0] - offset - 1) + "|", end="")
                offset = dpart[0]
            if verbose:
                print("[" + str(types[dparts[len(dparts) - j - 1][0]]) + "] " + str(exdiff[dparts[len(dparts) - j - 1][0]][:5]))

        times = str(len(msgs[msg])) + " times"
        toh += len(msg) + oh
        if len(msg):
            print("=", colors["cyan"] + "compression ratio " + str(round(100 * (len(msg) + oh) / (len(msg) * len(msgs[msg])))) + "% / " + times + colors["reset"])
        else:
            print("=", colors["cyan"] + "no compression ratio / empty line" + colors["reset"])

        #retlist.append((msg, exdiff))
        retlist.append((msg, msgs[msg]))

    tlen = 0
    tlines = 0
    for msg in msgs:
        for r in msgs[msg]:
            tlen += len(r) + 1
            tlines += 1
    print("TOTAL", tlines, "lines", tlen, "bytes → compressed", len(msgs), "lines", toh, "bytes", round(100 * toh / tlen, 2), "%")

    return retlist

def persist(retlist):
    #print(retlist)
    os.makedirs("_index.dir", exist_ok=True)
    f = open("_index.dir/index", "w")
    for i, entry in enumerate(retlist):
        msg, msgs = entry
        print(i, msg, file=f)
        fr = open("_index.dir/" + str(i), "w")
        for r in msgs:
            print(r, file=fr)
        fr.close()
    f.close()
