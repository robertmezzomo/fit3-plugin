# Fit3-App com instalação num relógio modificado

Depois de instalar um firmware do fit3-toolkit (o teclado, os apps), o relógio deixa o serviço de
arquivos (SPP) sempre aberto e passa a **recusar o pedido BT_OPEN** do Fit3-App. Com isso, o
instalador de firmware e o gerenciador de arquivos do Fit3-App param na hora, com
`Band rejected OTA request 2 (reason 0)` e `Watch rejected file channel`. Visto num relógio real em
2026-11-16.

`fit3app-bt-open.patch` muda só isso no [Fit3-App](https://github.com/yuriyurin/Fit3-App) (commit `1ac39f0`):

- se o relógio recusar o BT_OPEN, o app tenta conectar direto no serviço de arquivos. Se o serviço
  estiver realmente fechado, essa conexão falha e nada é gravado;
- a recusa do primeiro passo (o anúncio do firmware) continua parando a instalação;
- o app ganha outro nome de pacote (`io.github.yuriyurin.fit3companion.fit3plugin`) e o rótulo
  "Fit3 App (fit3-plugin)", para ser instalado **ao lado** do original;
- um teste novo (`refusedBtOpenStillTriesTheSerialService`).

```sh
fit3app/build.sh Fit3App-fit3plugin.apk
```

Os testes do protocolo (`Fit3FirmwareSessionTest`, `BandFileTransportTest`, 16 no total) passam.
**Num relógio real (2026-11-16):** instalou o firmware `R390XXU0AZA3_teclado_sensores.bin` num relógio
que já rodava um firmware do fit3-toolkit e recusava o BT_OPEN.

## Licença

O Fit3-App é GPL-3.0-only, e este patch é uma obra derivada dele: **o patch e o APK gerado seguem a
GPL-3.0**, não a licença Apache do resto deste repositório. O código-fonte completo é o Fit3-App no
commit indicado mais este patch.
