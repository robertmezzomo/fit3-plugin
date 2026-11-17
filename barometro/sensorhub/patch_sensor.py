#!/usr/bin/env python3
"""patch_sensor.py: patches no firmware do processador de sensores para liberar a taxa do acelerômetro.
Dois ajustes de 1 byte cada, controlados por variáveis de ambiente:
  MODE_LN=1 (padrão)  -> coloca o ICM-42670 em modo baixo ruído (reg 0x4e bits[1:0]: 2->3) em icm42670 init (0x260528b8)
  ODR_CODE=5 (padrão) -> força o código de ODR do chip para taxas pedidas >50 (setodr 0x2603061a); 5=1600 6=800 7=400 8=100(estoque)
Refaz todos os CRCs do pacote. Baixo ruído é um modo válido do chip (gasta um pouco mais de bateria) e só
age ao ligar o sensor, nunca no boot. Reversível reinstalando o original. NÃO testado num relógio.

    python3 patch_sensor.py <toolkit>/src/firmware in.bin out.bin
"""
import os, sys, hashlib
HUB = "/user/ota/sensorhub/sensor_hub.bin"
B = 0x26000000
ODR_OFF = 0x2603061a - B;  ODR_OLD = b"\x08\x21"
MODE_OFF = 0x260528b8 - B + 2                 # imm8 do 'orr r3,r3,#2' (43 f0 [02] 03)

def main(a):
    if len(a) != 3: sys.exit("uso: patch_sensor.py <toolkit>/src/firmware in.bin out.bin")
    sys.path.insert(0, a[0]); import fwd
    p = fwd.Package.load(a[1]); raw = bytearray(p.raw(HUB)); changes = []
    if os.environ.get("ODR_CODE", "5") != "stock":
        code = int(os.environ.get("ODR_CODE", "5"))
        if raw[ODR_OFF:ODR_OFF+2] != ODR_OLD: sys.exit("setodr: bytes inesperados %s" % raw[ODR_OFF:ODR_OFF+2].hex())
        raw[ODR_OFF] = code; changes.append("ODR code=%d" % code)
    if os.environ.get("UNSKIP", "1") == "1":
        o = 0x260528fe - B                       # 'bls' que pula a config de filtro (reg 0x50) nas taxas altas -> NOP
        if raw[o:o+2] != b"\x2e\xd9": sys.exit("unskip: bytes inesperados %s" % raw[o:o+2].hex())
        raw[o:o+2] = b"\x00\xbf"; changes.append("roda config 0x50 em taxa alta")
    if os.environ.get("MODE_LN", "1") == "1":
        if raw[MODE_OFF] != 0x02: sys.exit("modo: byte inesperado em 0x260528ba: %#x (esperado 0x02)" % raw[MODE_OFF])
        raw[MODE_OFF] = 0x03; changes.append("modo baixo ruido")
    p.set_raw(HUB, bytes(raw)); p.save(a[2])
    fwd.Package.load(a[2])                      # re-valida CRCs
    print("escrito", a[2], "|", ", ".join(changes))
    print("sha256", hashlib.sha256(open(a[2], "rb").read()).hexdigest())

if __name__ == "__main__": main(sys.argv[1:])
