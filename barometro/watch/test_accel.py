# SPDX-License-Identifier: Apache-2.0
"""test_accel.py: the Acelerometro app (accel.c) in the fit3-toolkit emulator, with a simulated sensor hub that answers rate requests the way each
possible chip would (ICM-42670 or LSM6DSO). Checks that the app measures the rates, names the chip, reports the step and the noise, saves
/user/accel.bin and cleans up. What the real hub does with the requests is for the watch.

    F3_HOSTIMAGE=local/re/main-sensores.bin F3_TOOLKIT=. local/venv/bin/python -I <this file>"""
import math, os, random, struct, sys
TK = os.path.abspath(os.environ.get("F3_TOOLKIT", ".")); sys.path.insert(0, os.path.join(TK, "src", "emu")); os.chdir(TK)
from rig import Rig as _Rig, A
REC = 0x200fb4e4 + 0x10 * 0x30
LADDER = {"ICM-42670": [12.5, 25, 50, 100, 200, 400, 800, 1600], "LSM6DSO": [12.5, 26, 52, 104, 208, 416, 833, 1666, 3333, 6666]}

class Rig(_Rig):
    def __init__(self): super().__init__(os.environ.get("F3_HOSTIMAGE", "local/re/main-sensores.bin"))
    def create(self):
        scr = super().create(); self.rows = self.children(self.children(scr)[1]); return scr
    def manager_open(self, arg):
        create = self.e.u32(REC + 0x1c) & ~1; scr = self.e.call(create, arg); self.e.w32(REC + 0x10, scr)
        self.e.call(self.e.u32(REC + 0x24) & ~1, 0, 0, 0); self.scr, self.win = scr, self.e.u32(scr + 0x10); return scr

def run(chip, ok):
    r = Rig(); e = r.e; calls = []; rate = [50.0]
    def set_rate(em):
        req = em.arg(1); calls.append(("rate", em.arg(0), req))
        lad = LADDER[chip]; rate[0] = min([x for x in lad if x >= req] or [lad[-1]]); return 0
    e.hook(0x2c0f036c, lambda em: calls.append(("listen", em.arg(0), em.arg(1))) or 0)
    e.hook(0x2c0f03f0, lambda em: calls.append(("unlisten", em.arg(0), em.arg(1))) or 0)
    e.hook(0x2c0f04a0, set_rate)
    r.create(); names = [r.alltext(x) for x in r.rows]; idx = names.index(["Acelerometro"])
    r.click(r.rows[idx]); scr = r.manager_open(idx); st = e.u32(r.win + 16)
    lis = [c for c in calls if c[0] == "listen"]; cb = lis[0][2] & ~1
    ok(chip + ": listens to sensor 0", lis[0][1] == 0)
    rec = 0x20700000; acc = [0.0]; rnd = random.Random(1); t = [0]
    def run_ms(ms):
        for _ in range(ms // 50):
            acc[0] += rate[0] * 0.05; n = int(acc[0]); acc[0] -= n
            for _ in range(n):
                t[0] += 1
                # int16 counts at +-4 g (8192 LSB/g): gravity on z, noise of ~3 counts, a 150 Hz vibration of 20 counts
                vals = [rnd.gauss(0, 3), rnd.gauss(0, 3), 8192 + rnd.gauss(0, 3) + 20 * math.sin(2 * math.pi * 150 * t[0] / max(rate[0], 1))]
                e.write(rec, bytes([0]) + bytes(7) + struct.pack("<3i", *[int(round(v)) for v in vals]) + bytes(20))
                e.call(cb, rec)
            r.tick += 50; r.timer_cb()
    run_ms(1000)
    go = [k for k in r.children(scr) if r.alltext(k) == ["Testar"]][0]; r.click(go)
    run_ms(3000 * 9 + 500)
    t_ = r.alltext(scr); print("   ", t_)
    ok(chip + ": the chip is named", ("Chip: " + chip) in t_, t_)
    f = r.files.get("/user/accel.bin", b"")
    ok(chip + ": /user/accel.bin saved", len(f) > 100, len(f))
    if f:
        magic, ver, chipno, ncap = struct.unpack_from("<4I", f, 0); meas = struct.unpack_from("<9I", f, 16)
        print("    medido:", meas)
        ok(chip + ": file header", magic == 0x31434341 and chipno == (1 if chip == "ICM-42670" else 2) and ncap == 340, (hex(magic), chipno, ncap))
        ok(chip + ": measured rates follow the ladder", all(abs(m - min([x for x in LADDER[chip] if x >= q] or [LADDER[chip][-1]])) <= 0.06 * m + 2 for q, m in zip((25, 50, 100, 200, 400, 800, 1600, 3200, 6400), meas)), meas)
    ok(chip + ": step 1 (int counts) shown", any(x.startswith("passo 1/1/1") for x in t_), t_)
    calls.clear(); e.call(A["obj_del"], scr)
    ok(chip + ": closing stops listening and frees the state", ("unlisten", 0, lis[0][2]) in calls and st in r.freed, calls)

def main():
    res = []; ok = lambda name, cond, obs="": (res.append(bool(cond)), print("%s %s %s" % ("PASS" if cond else "FAIL", name, obs if not cond else "")))
    for chip in LADDER: run(chip, ok)
    print("%d/%d passed" % (sum(res), len(res))); return 0 if all(res) else 1

if __name__ == "__main__": sys.exit(main())
