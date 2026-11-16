#!/usr/bin/env python3
"""patch_odr.py: ETAPA 1 (experimento). A partir de um pacote FWD do fit3-toolkit (ex.: o firmware
teclado+sensores), muda UM byte no firmware do processador de sensores para o ICM-42670 rodar a
1600 Hz em vez de travar em ~100, e refaz todos os CRCs.

    python3 patch_odr.py <TOOLKIT>/src/firmware R390XXU0AZA3_teclado_sensores.bin R390XXU0AZA3_accel1600.bin

O que muda (barometro/firmware.md): em `icm42670_setodr` (0x260305e4), para qualquer taxa pedida acima
de 50, o código de ODR escrito no chip passa de 8 para 5 (tabela do ICM-42670: 5 = 1600 Hz). Instrução
`movhs r1,#8` (bytes 08 21) em 0x2603061a -> `movs r1,#5` (05 21). Nada mais é tocado.

Seguro quanto à memória (não mexe no lote de 50 amostras nem em buffers) e só age quando o sensor é
ligado, nunca na inicialização: o relógio liga e pode ser reinstalado de qualquer jeito. Reversível
reinstalando o firmware original. Enquanto estiver instalado, o acelerômetro roda mais rápido, o que
pode bagunçar contagem de passos e detecção de queda; reinstale o original para voltar ao normal.

NÃO testado num relógio: o app Acelerometro mede a taxa que realmente chega."""
import sys, hashlib
HUB = "/user/ota/sensorhub/sensor_hub.bin"
OFF = 0x2603061a - 0x26000000      # image base 0x26000000
OLD = b"\x08\x21"                  # movhs r1,#8
ODR_CODE = int(__import__("os").environ.get("ODR_CODE", "5"))   # 5=1600 6=800 7=400 8=100(estoque)
NEW = bytes([ODR_CODE, 0x21])    # movs r1,#<code>

def main(argv):
    if len(argv) != 3:
        sys.exit("uso: patch_odr.py <toolkit>/src/firmware <in.bin> <out.bin>")
    sys.path.insert(0, argv[0]); import fwd
    p = fwd.Package.load(argv[1])
    raw = bytearray(p.raw(HUB))
    if raw[OFF:OFF+2] != OLD:
        sys.exit("bytes inesperados em 0x2603061a: %s (esperado 0821). Pacote errado?" % raw[OFF:OFF+2].hex())
    raw[OFF:OFF+2] = NEW
    p.set_raw(HUB, bytes(raw))
    p.save(argv[2])
    chk = fwd.Package.load(argv[2])          # reload re-valida todos os CRCs
    assert chk.raw(HUB)[OFF:OFF+2] == NEW
    print("escrito", argv[2])
    print("sha256", hashlib.sha256(open(argv[2], "rb").read()).hexdigest())

if __name__ == "__main__":
    main(sys.argv[1:])
# Uso com código alternativo:  ODR_CODE=7 python3 patch_odr.py <toolkit>/src/firmware in.bin out.bin
