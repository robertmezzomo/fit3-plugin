# SPDX-License-Identifier: Apache-2.0
"""test_baro.py: the Barometro app (baro.c) on the real firmware in the fit3-toolkit emulator, with simulated barometer samples.

Run from the patched fit3-toolkit checkout (barometro/watch/build.sh prints the commands):
    F3_HOSTIMAGE=local/re/main-sensores.bin local/venv/bin/python -I <this file>

It plays the window manager (as test_host.py does), opens the app, calls the sensor callback the app registered with records like the ones the sensor hub
sends (byte 0 = sensor 3, +8 a float pressure in hPa, +12 a float temperature), and checks the screen, the recording and the cleanup. It cannot show
what the real sensor hub sends: that is for the watch."""
import math, os, struct, sys
TK = os.path.abspath(os.environ.get("F3_TOOLKIT", ".")); sys.path.insert(0, os.path.join(TK, "src", "emu")); sys.path.insert(0, os.path.join(TK, "src", "f3x"))
os.chdir(TK)
from rig import Rig as _Rig, A
REC = 0x200fb4e4 + 0x10 * 0x30

class Rig(_Rig):                                                                  # as in test_host.py (which runs its own tests when imported)
    def __init__(self): super().__init__(os.environ.get("F3_HOSTIMAGE", "local/re/main-sensores.bin"))
    def create(self):
        scr = super().create(); self.rows = self.children(self.children(scr)[1]); return scr
    def manager_open(self, arg):
        create = self.e.u32(REC + 0x1c) & ~1; scr = self.e.call(create, arg); self.e.w32(REC + 0x10, scr)
        self.e.call(self.e.u32(REC + 0x24) & ~1, 0, 0, 0); self.scr, self.win = scr, self.e.u32(scr + 0x10); return scr

def main():
    r = Rig(); e = r.e; res = []
    ok = lambda name, cond, obs="": (res.append(bool(cond)), print("%s %s %s" % ("PASS" if cond else "FAIL", name, obs)))
    calls = []
    e.hook(0x2c0f036c, lambda em: calls.append(("listen", em.arg(0), em.arg(1))) or 0)
    e.hook(0x2c0f03f0, lambda em: calls.append(("unlisten", em.arg(0), em.arg(1))) or 0)
    e.hook(0x2c0f04e4, lambda em: calls.append(("mode", em.arg(0), em.arg(1))) or 0)
    r.create(); names = [r.alltext(x) for x in r.rows]
    ok("the hub lists the app", ["Barometro"] in names, names)
    idx = names.index(["Barometro"]); r.click(r.rows[idx]); scr = r.manager_open(idx); st = e.u32(r.win + 16)
    ok("the app opened (state set)", st != 0, hex(st))
    lis = [c for c in calls if c[0] == "listen"]
    ok("it listens to sensor 3 and asks for mode 1 (100 Hz)", len(lis) == 1 and lis[0][1] == 3 and ("mode", 3, 1) in calls, calls)
    cb = lis[0][2] & ~1
    rec = 0x20700000
    def feed(n, amp_pa=1.0, f=40.0, t0=[0]):
        for i in range(n):
            k = t0[0]; t0[0] += 1
            p = 1013.25 + amp_pa / 100.0 * math.sin(2 * math.pi * f * k / 100.0)
            e.write(rec, bytes([3]) + bytes(7) + struct.pack("<ff", p, 25.5) + bytes(8))
            e.call(cb, rec); r.tick += 10
            if k % 5 == 4: r.timer_cb()
    feed(250)
    t = r.alltext(scr); print("  screen:", t)
    ok("pressure shown in hPa", any(x.startswith("1013.") and x.endswith("hPa") for x in t), t)
    ok("rate ~100 samples/s", any(x.startswith(("99/s", "100/s", "101/s")) for x in t), t)
    lvl = [x for x in t if "nivel" in x]
    ok("a 1 Pa sine reads as ~0.7 Pa RMS", lvl and 0.5 <= float(lvl[0].split("nivel ")[1].split(" ")[0]) <= 0.9, lvl)
    ok("raw words shown (float of 1013.25 starts with 447d)", any(x.startswith("447d") for x in t), t)
    rec_btn = [k for k in r.children(scr) if r.alltext(k) == ["Gravar"]]
    r.click(rec_btn[0]); feed(1010)
    f = r.files.get("/user/baro.bin", b"")
    ok("10 s recorded and saved to /user/baro.bin (216-byte header + 1000 words)", len(f) == 216 + 4000, len(f))
    if f:
        magic, ver, count = struct.unpack_from("<III", f, 0); first = f[24:24 + 24]
        vals = struct.unpack_from("<%df" % count, f, 216)
        ok("header and samples", magic == 0x4f524142 and ver == 1 and count == 1000 and first[0] == 3 and abs(vals[0] - 1013.25) < 0.02, (hex(magic), ver, count, vals[:3]))
    t = r.alltext(scr); ok("status says saved", any(x.startswith("Salvo") for x in t), t)
    calls.clear(); e.call(A["obj_del"], scr)
    ok("closing the app sets mode 0 and stops listening with the same callback", ("mode", 3, 0) in calls and ("unlisten", 3, lis[0][2]) in calls, calls)
    ok("the state was freed", st in r.freed)
    print("%d/%d passed" % (sum(res), len(res))); return 0 if all(res) else 1

if __name__ == "__main__": sys.exit(main())
