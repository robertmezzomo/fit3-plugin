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

## Acelerômetro (ICM-42670) no processador de sensores

Medido num relógio real (2026-11-16, app Acelerometro): pedidos de 25/50/100 chegam como 25/50/~100;
qualquer pedido acima de 100 chega como **~100 leituras/s**. Os 25 e 50 exatos apontam para o
ICM-42670 (o LSM6DSO daria 26 e 52), mas o repasse pode ser cadenciado pelo próprio processador de
sensores, então não é prova.

- `icm42670_setodr(sensorid, odr)` em `0x260305e4` (referência à string `icm42670_setodr: sensorid=%d, odr=%d`):
  `odr ≤ 12,5` → 12,5 (código 11); `≤ 25` → 25 (código 10); `< 51` → 50 (código 9); **qualquer outro → 100
  (código 8)**. O código vai para uma função da ROM do chip (veneer `0x26035ef0` → `0x06052cad`), e
  `odr/25` é guardado no byte `0x2017d5eb`. Pela tabela de ODR da TDK (5 = 1,6 kHz … 8 = 200 Hz …
  12 = 12,5 Hz) o chip estaria rodando ao dobro do valor pedido; não confirmado.
- `0x26030c5c` lê uma amostra dos registradores de dados, mas **só é chamada pela calibração**
  (`icm42670_acc_gryo_get_average_data`). Não é o caminho normal. (Uma versão anterior deste arquivo
  dizia o contrário.)
- O caminho normal é `0x260308e8`: um tratador chamado **uma vez por amostra do chip** (recebe flags,
  um carimbo de tempo de 16 bits em `+4` e x/y/z `int16` em `+6/+8/+10`). Ele converte para `float` e
  acrescenta um registro de 32 bytes num lote em `0x201a2d28` (contador em `+0x648`), **com no máximo 50
  amostras por lote**: o que passar disso antes de o lote ser enviado é descartado. O giroscópio usa
  um lote igual em `+0x650` (contador em `+0xc90`).
- O firmware do processador de sensores não tem CRC próprio visível: o cabeçalho (`0xbe57ec1c`, `0x40000`,
  `0`, fim `0x260ae580`) e o rodapé (`0xbe57341d`, base `0x26000000`) parecem constantes. O pacote tem o
  CRC32 do componente, que o fit3-toolkit sabe refazer. Se o carregador verifica mais alguma coisa, não
  se sabe.

Para chegar a kHz é preciso: (1) liberar ODRs maiores em `icm42670_setodr`; (2) descobrir de quanto em
quanto tempo o lote de 50 é enviado, porque a 1.600 Hz ele enche em 31 ms; (3) conferir se o canal até o
processador principal aguenta 1.600 registros de 32 bytes por segundo, ou gravar num buffer próprio e
enviar depois.
