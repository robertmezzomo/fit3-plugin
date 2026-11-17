# SPDX-License-Identifier: Apache-2.0
"""test_diag.py: o app Diag (diag.c) no emulador, com amostras simuladas. Confere que /user/diag.txt sai legível,
com os registros crus e a taxa medida por passo.
    F3_HOSTIMAGE=local/re/main-diag.bin F3_TOOLKIT=. local/venv/bin/python -I <este arquivo>"""
import os, struct, sys
TK = os.path.abspath(os.environ.get("F3_TOOLKIT", ".")); sys.path.insert(0, os.path.join(TK, "src", "emu")); os.chdir(TK)
from rig import Rig
REC = 0x200fb4e4 + 0x10 * 0x30

def main():
    r = Rig(os.environ.get("F3_HOSTIMAGE", "local/re/main-diag.bin")); e = r.e; calls = []; rate = [50.0]
    e.hook(0x2c0f036c, lambda em: calls.append(em.arg(1)) or 0); e.hook(0x2c0f03f0, lambda em: 0)
    e.hook(0x2c0f04a0, lambda em: rate.__setitem__(0, 0.0 if em.arg(1) > 400 else min(em.arg(1), 416.0)) or 0)
    scr = r.create(); rows = r.children(r.children(scr)[1]); i = [r.alltext(x) for x in rows].index(["Diag"])
    r.click(rows[i]); cr = e.u32(REC + 0x1c) & ~1; scr = e.call(cr, i); e.w32(REC + 0x10, scr)
    e.call(e.u32(REC + 0x24) & ~1, 0, 0, 0); r.scr, r.win = scr, e.u32(scr + 0x10)
    cb = calls[0] & ~1; rec = 0x20700000; acc = [0.0]; t = [0]
    def feed(ms):
        for _ in range(ms // 50):
            acc[0] += rate[0] * 0.05; k = int(acc[0]); acc[0] -= k
            for _ in range(k):
                t[0] += 1; b = bytearray(40); struct.pack_into("<H", b, 4, t[0] & 0xffff); struct.pack_into("<3f", b, 8, 0.01, 0.01, 9.8)
                e.write(rec, bytes(b)); e.call(cb, rec)
            r.tick += 50; r.timer_cb()
    r.click([x for x in r.children(scr) if r.alltext(x) == ["Rodar diag"]][0])
    feed(1600 * 7 + 300)
    f = r.files.get("/user/diag.txt", b"")
    res = []; ok = lambda n, c: (res.append(bool(c)), print(("PASS " if c else "FAIL ") + n))
    ok("diag.txt gerado", len(f) > 500)
    ok("tem o passo de 50 Hz medido", b"pedido 50 Hz : 75 amostras" in f)
    ok("mostra 0 amostras acima de 400", b"(nenhuma amostra)" in f or b"pedido 1600 Hz : 0" in f)
    ok("dumpa registros de 40 bytes (80 hex + espacos)", b"0000 cdcc1c41" in f or b" 00000000 01000000 " in f)
    print(f.decode("latin1")[:400])
    print("%d/%d passed" % (sum(res), len(res))); return 0 if all(res) else 1

if __name__ == "__main__":
    sys.exit(main())
