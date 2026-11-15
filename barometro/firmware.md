# Barômetro no firmware R390XXU0AZA3 (engenharia reversa)

Endereços do pacote `R390XXU0AZA3` (SHA-256 `25e692ba…`). Achados por referência cruzada de strings
e leitura do código (capstone), **não** verificados num relógio. Imagem principal em `0x2c080000`,
firmware do processador de sensores (`/user/ota/sensorhub/sensor_hub.bin`) em `0x26000000`.

## Processador principal

| Endereço | O quê | Evidência |
|---|---|---|
| `0x2c0f036c` | `sensor_listen(id, cb)`: registra `cb` para o sensor `id` e manda `{0, id}` ao processador de sensores | string `service_sensor_regist_listener: sensor_status error`; usado pelo teste de fábrica `[mmi] start baro` com `id = 3` |
| `0x2c0f03f0` | `sensor_unlisten(id, cb)` | o par de `sensor_listen` no mesmo teste |
| `0x2c0f04e4` | `sensor_mode(id, m)`: `m` 0→msg 3, 1→msg 4, 2/3→msg 5, 9→msg 7 | leitura do código |
| `0x2c0f04a0` | `sensor_rate(id, u16)`: msg `{6, id, u16}` | leitura do código; não usado pelo app |
| `0x2c0f06dc` | `sensor_runtest(id, cmd, arg, out)`: msg de 8 bytes, espera resposta até 6 s | string `service_sensor_runtest: sensor_status error` |
| `0x2c0f0474` | entrega um registro a cada `cb` cadastrado para o sensor | leitura do código |

Sensor `3` = barômetro (o teste de fábrica `[mmi] start baro` usa `sensor_listen(3, …)`).

Os dados chegam em pacotes `{2, id, n, …}` com `n` registros. O registro do barômetro tem **16 bytes**.
`cb` recebe um bloco com `[0] = id` e o registro a partir de `+8`. O teste de fábrica lê `+8` e `+12`.
O app supõe que `+8` é a pressão em `float` (hPa) e mostra as duas palavras em hexadecimal para conferir.

## Processador de sensores

- Drivers de barômetro: `barometer_lps27hhtw` (ST LPS27HHTW), `barometer_gmp108`, `barometer_mspc110`.
- `lps27hhtw_setmode` (`0x260263e8`): modo `1` guarda `lps27h_mode = 1`, qualquer outro guarda `3`.
- `lps27hhtw_setodr` (`0x2602635c`): escreve `CTRL_REG1` com o campo ODR = `0x60` (**100 Hz**) se
  `lps27h_mode == 1`, senão `0x10` (**1 Hz**).
- Tratador das mensagens do processador principal: `0x260333ec` (tipo 0 abre, 1 fecha, 3/4/5 modo 0/1/2,
  6 taxa `u16`, …).

Ou seja, com o LPS27HHTW o máximo deste caminho é **100 leituras por segundo**: só frequências até 50 Hz.
Os outros dois modelos não foram analisados.
