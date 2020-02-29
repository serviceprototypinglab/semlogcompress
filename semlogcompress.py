import difflib
import sys
import os
import re

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
    if fn == "-":
        f = sys.stdin
    else:
        f = open(fn)

    msgs = process_internal(f, verbose, limit_lines, fn)

    f.close()

    return msgs

def process_internal(f, verbose, limit_lines, fnx):
    msgs = {}

    i = 0
    try:
        for line in f:
            i += 1
            if limit_lines is not None and i > limit_lines:
                break

            process_line(line, msgs, verbose, i, fnx)
    except KeyboardInterrupt:
        print("(closing input)")

    return msgs

def process_line(line, msgs, verbose, i, fnx):
    line = line.strip()
    #print(line)
    # m - month, d - day, t - time, ip - ipv4 address, dev - device; dt - date
    # TODO eliminate fnx parameter and use auto-detection of fields
    if "fw" in fnx:
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

def typeget(s):
    if s.isdigit():
        return "digit"
    elif s.isalpha():
        return "alpha"
    else:
        return "mixed"

def printpatterns(dparts, r, extra=""):
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
    print("=", dblocks, "(log line with patterns) " + extra)
    return oh

def handle(msgs, verbose):
    retlist = []

    if verbose:
        print("---")
    toh = 0
    for msg in sorted(msgs):
        types = {}

        if verbose:
            print(colors["yellow"] + "X " + msg + " (cluster)" + colors["reset"])
        alldiff = {}
        exdiff = {}
        for r in msgs[msg]:
            if verbose:
                print("*", r, "(raw log line)")
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
                print("→", cblocks, "(diffed log line) (diff count D: " + str(len(diff)) + ")")
                print("D", colors["magenta"] + str(diff) + colors["reset"])

        dparts = sorted(alldiff.items())
        if verbose:
            print("#", dparts)
        oh = printpatterns(dparts, r)

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

        dpartsext = dparts[:]
        typesext = {}
        #print("R", r, "T", types)
        laststop = None
        for j in range(len(dpartsext)):
            if dparts[j][1]:
                start = dparts[j][0]
                stop = start + len(dparts[j][1]) - 1
                t = types[dparts[j][0]]
                #print(dparts[j], t, start, "..", stop)
                estart = start
                estop = stop
                for k in range(1, 99):
                    if (laststop and start - k == laststop) or start - k < 0:
                        break
                    if typeget(r[start - k]) == t:
                        estart -= 1
                    else:
                        break
                for k in range(1, 99):
                    if (j < len(dpartsext) - 1 and stop + k == dparts[j + 1][0]) or stop + k == len(r):
                        break
                    if typeget(r[stop + k]) == t:
                        estop += 1
                    else:
                        break
                #print("==> extended type range", estart, estop)
                dpartsext[j] = (estart, "*" * (estop - estart + 1))
                typesext[estart] = types[start]
                laststop = estop
        if verbose:
            print("#", dpartsext, "extended")
        dpartsmer = []
        for dpart in dpartsext:
            dpartprev = None
            if len(dpartsmer):
                dpartprev = dpartsmer[-1]
            if dpartprev and types[dpart[0]] == types[dpartprev[0]] and dpartprev[0] + len(dpartprev[1]) == dpart[0]:
                dpartmer = (dpartprev[0], "*" * (len(dpartprev[1]) + len(dpart[1])))
                #print("merge", dpartsmer[-1], dpart, "=>", dpartmer)
                dpartsmer[-1] = dpartmer
            else:
                dpartsmer.append(dpart)
        if verbose:
            print("#", dpartsmer, "extended and merged")
        printpatterns(dpartsmer, r, "(extended and merged)")

        times = str(len(msgs[msg])) + " times"
        toh += len(msg) + oh
        if len(msg):
            print("=", colors["cyan"] + "compression ratio " + str(round(100 * (len(msg) + oh) / (len(msg) * len(msgs[msg])))) + "% / " + times + colors["reset"])
        else:
            print("=", colors["cyan"] + "no compression ratio / empty line" + colors["reset"])

        #retlist.append((msg, exdiff))
        retlist.append((msg, msgs[msg]))

        knowledge = {}
        lastpos = 0
        lastlen = 0
        for dpart in dpartsmer:
            if not len(dpart[1]):
                continue
            semtype = "unknown"
            if types[dpart[0]] == "digit" and len(dpart[1]) in (4, 5):
                semtype = "portnumber"
            i = 1
            semtypeorig = semtype
            while semtype in knowledge:
                i += 1
                semtype = semtypeorig + str(i)
            semre = ""
            if semtypeorig == "portnumber":
                semre = "(\\d{1," + str(len(dpart[1])) + "})"
            else:
                semre = "(.{1," + str(len(dpart[1])) + "})"
            regex = msg[lastpos + lastlen:dpart[0] + 1] + semre
            if verbose:
                print(">", semtype, regex)
            data = []
            if verbose:
                print(">>", lastpos, "..", dpart[0], regex)
            for r in msgs[msg]:
                sr = re.search(regex, r)
                if sr:
                    m = sr.group(1)
                    if verbose:
                        print("   M", m)
                    data.append(m)
            #for r in msgs[msg]:
            #    data.append(r[dpart[0]:dpart[0] + len(dpart[1])])
            knowledge[semtype] = data
            lastpos = dpart[0]
            lastlen = len(dpart[1]) + 1
        print(">>> knowledge", knowledge)

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
