# SPDX-License-Identifier: Apache-2.0
"""test_recorder.py: o app Gravador (recorder.c) no emulador do fit3-toolkit, com amostras simuladas do acelerometro.
Abre o app, grava alguns segundos e confere que /user/audio.bin sai no formato F3R1 (magic, taxa medida, 3 canais, n, int16 x/y/z).
    F3_HOSTIMAGE=local/re/main-rec.bin F3_TOOLKIT=. local/venv/bin/python -I <este arquivo>"""
import math, os, struct, sys
TK = os.path.abspath(os.environ.get("F3_TOOLKIT", ".")); sys.path.insert(0, os.path.join(TK, "src", "emu")); os.chdir(TK)
from rig import Rig, A
REC = 0x200fb4e4 + 0x10 * 0x30

def main():
    r = Rig(os.environ.get("F3_HOSTIMAGE", "local/re/main-rec.bin")); e = r.e; calls = []; rate = [1600.0]
    res = []; ok = lambda n, c, o="": (res.append(bool(c)), print(("PASS " if c else "FAIL ") + n + ("" if c else "  " + str(o))))
    e.hook(0x2c0f036c, lambda em: calls.append(("listen", em.arg(0), em.arg(1))) or 0)
    e.hook(0x2c0f03f0, lambda em: calls.append(("unlisten", em.arg(0))) or 0)
    e.hook(0x2c0f04a0, lambda em: (calls.append(("rate", em.arg(1))), rate.__setitem__(0, min(1600.0, em.arg(1)))) and 0)
    scr = r.create(); rows = r.children(r.children(scr)[1]); i = [r.alltext(x) for x in rows].index(["Gravador"])
    r.click(rows[i]); cr = e.u32(REC + 0x1c) & ~1; scr = e.call(cr, i); e.w32(REC + 0x10, scr)
    e.call(e.u32(REC + 0x24) & ~1, 0, 0, 0); r.scr, r.win = scr, e.u32(scr + 0x10)
    st = e.u32(r.win + 16); cb = [c for c in calls if c[0] == "listen"][0][2] & ~1
    ok("abriu, ouve sensor 0, pede taxa maxima", ("rate", 6400) in calls and any(c[0] == "listen" and c[1] == 0 for c in calls), calls)
    rec = 0x20700000; acc = [0.0]; t = [0]
    def feed(ms):
        for _ in range(ms // 100):
            acc[0] += rate[0] * 0.1; k = int(acc[0]); acc[0] -= k
            for _ in range(k):
                t[0] += 1; z = 9.8 + 0.3 * math.sin(2 * math.pi * 300 * t[0] / rate[0])
                e.write(rec, bytes([0]) + bytes(7) + struct.pack("<3f", 0.01, 0.01, z) + bytes(20)); e.call(cb, rec)
            r.tick += 100; r.timer_cb()
    feed(1000)
    r.click([x for x in r.children(scr) if r.alltext(x) == ["Gravar"]][0]); feed(5600)
    f = r.files.get("/user/audio.bin", b"")
    ok("audio.bin salvo", len(f) > 16, len(f))
    if f:
        magic, fs, ch, n = struct.unpack_from("<4I", f, 0)
        print("   header: magic=%s fs=%d ch=%d n=%d bytes=%d" % (hex(magic), fs, ch, n, len(f)))
        ok("F3R1, 3 canais, taxa ~1600", magic == 0x31523346 and ch == 3 and 1400 < fs < 1700, (hex(magic), ch, fs))
        ok("tamanho = header + n*3*2 int16", len(f) == 16 + n * 3 * 2, len(f))
        zs = [struct.unpack_from("<h", f, 16 + (k * 3 + 2) * 2)[0] for k in range(min(n, 2000))]
        ok("eixo Z varia (tom de 300 Hz capturado)", max(zs) - min(zs) > 100, (min(zs), max(zs)))
    calls.clear(); e.call(A["obj_del"], scr)
    ok("ao sair, baixa a taxa e para de ouvir", ("rate", 50) in calls and ("unlisten", 0) in calls, calls)
    ok("estado liberado", st in r.freed)
    print("%d/%d passed" % (sum(res), len(res))); return 0 if all(res) else 1

if __name__ == "__main__":
    sys.exit(main())
