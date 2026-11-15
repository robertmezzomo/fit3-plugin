# Barômetro como microfone (prova de conceito)

Tenta usar o barômetro do Fit3 como microfone: converte leituras de pressão em áudio e filtra o
que sobra da voz. É um experimento. As contas e a simulação abaixo indicam que **não dá para
entender fala** por esse caminho. No melhor caso, dá para saber **quando** alguém está falando.

## O sensor

O firmware do processador de sensores (`/user/ota/sensorhub/sensor_hub.bin`, dentro do pacote
R390XXU0AZA3) tem drivers para três barômetros: `barometer_lps27hhtw` (ST LPS27HHTW),
`barometer_gmp108` e `barometer_mspc110`. O barômetro fica ligado a esse processador, não ao
processador principal onde roda o código do fit3-toolkit.

## Os arquivos

- `baro_mic.py`: o conversor. Recebe leituras de pressão (CSV, em hPa ou Pa) e gera um WAV de 16 kHz:
  tira a média, aplica um passa-altas de 15 Hz (remove clima, altitude e movimento do braço), um
  passa-baixas logo abaixo da metade da taxa de amostragem, uma redução de ruído espectral e, por fim,
  normaliza e converte para 16 kHz.

  ```sh
  python3 baro_mic.py leituras.csv --fs 200 -o voz.wav
  ```

- `simulate_fit3_baro.py`: passa uma gravação de voz (ou um texto sintetizado com `espeak-ng`) por um
  modelo do barômetro e depois pelo conversor. Grava os WAVs e mostra os números.

  ```sh
  python3 simulate_fit3_baro.py --text "Oi, tudo bem? Estou chegando em dez minutos." --spl 100 94 85 70 -o resultados
  python3 simulate_fit3_baro.py --wav minha_voz.wav --spl 85 -o resultados
  ```

  Precisa de `numpy`, `scipy` e, para `--text`, de `espeak-ng`.

O modelo usa valores típicos de datasheet de um barômetro de relógio, não medições de um Fit3:
200 leituras por segundo, ~0,7 Pa de ruído e resolução de 1/4096 hPa. `--avg 1` faz cada leitura ser
a média da pressão no intervalo, como acontece num sensor com média interna. `--avg 0` faz uma leitura
instantânea, em que as frequências altas se dobram para baixo em vez de sumir. Esse é o melhor caso.

## Resultado da simulação (voz sintetizada, 2026-11-15)

Só **0,25%** da energia da fala cai na faixa que um sensor de 200 Hz enxerga (até 100 Hz).

| Fala no relógio | Pressão | Com média (realista) | | Instantâneo (melhor caso) | |
|---|---|---|---|---|---|
| | | SNR no sensor | Envelope | SNR no sensor | Envelope |
| 100 dB (gritando colado) | 2 Pa | −9,9 dB | 0,16 | +7,5 dB | 0,81 |
| 94 dB (boca colada) | 1 Pa | −15,7 dB | 0,33 | +1,6 dB | 0,79 |
| 85 dB (pulso a ~5 cm da boca) | 0,36 Pa | −25,1 dB | 0,12 | −7,8 dB | 0,47 |
| 70 dB (~30 cm) | 0,06 Pa | −38,9 dB | 0,00 | −22,8 dB | 0,06 |

*SNR: potência da fala dividida pela do ruído, na faixa útil (0 dB = iguais). Envelope: correlação
entre o volume do sinal processado e o volume da fala original (1 = acompanha, 0 = não acompanha).*

![Espectrogramas](../docs/img/barometro-espectrogramas.png)

Conclusão: palavras não sobrevivem. Mesmo um sensor perfeito, sem ruído, a 200 Hz só guarda um zumbido
grave sem as frequências que distinguem as vogais e consoantes. Com a boca praticamente encostada no
relógio e no melhor caso de amostragem, o volume do sinal acompanha a fala (0,8). Isso serve para
**detectar voz ou sopro**, não para transcrever.

## No relógio: o app "Barometro"

`watch/baro.c` é um app para o Application Hub do fit3-toolkit (veja [firmware.md](firmware.md)):

- liga o barômetro pelo serviço de sensores do próprio firmware e pede o modo de 100 Hz;
- mostra a pressão, quantas leituras chegam por segundo, as duas palavras cruas do registro, uma
  onda das variações rápidas (altura total = 2 Pa) e o nível delas;
- **Gravar** guarda 1000 leituras (~10 s) em `/user/baro.bin`;
- **Modo 100 Hz / Modo 1 Hz** troca o modo;
- ao sair, volta o sensor ao modo 0 e para de ouvir.

```sh
barometro/watch/build.sh caminho/para/stock-aza3.bin R390XXU0AZA3_teclado_barometro.bin
```

Gera o firmware com o teclado **e** o app (SHA-256 esperado
`4f3a37de64e75c510570af22b0ae0c865507e59f8fa5f7c6be4d47814e1b3a86`). O app substitui o Application Hub
vazio; o Relógio Mundial continua substituído.

Depois de gravar, baixe `/user/baro.bin` com o gerenciador de arquivos do Fit3-App e converta:

```sh
python3 baro_mic.py baro.bin -o voz.wav
```

O `baro_mic.py` mede a taxa real a partir da gravação, grava também um CSV e mostra os primeiros
registros crus.

| O quê | Verificado em |
|---|---|
| Endereços e formato dos dados | leitura do firmware |
| App: tela, taxa, nível, gravação, arquivo, desligamento (`watch/test_baro.py`, 12 verificações) | simulador, com leituras simuladas |
| O app num relógio real, e o que o processador de sensores realmente entrega | **ainda não testado** |

Riscos próprios deste app: ele manda o barômetro para o modo de 100 Hz e, ao sair, para o modo 0.
Se o relógio usava outro modo, ele fica assim até reiniciar. Reiniciar o relógio restaura o normal.
A gravação faz uma escrita de ~4 KB; o fit3-toolkit relata reinícios com escritas grandes e frequentes.

## Próximos passos possíveis

- Se o relógio mostrar ~100 leituras por segundo, gravar falando com o relógio colado na boca, e também
  soprando, e comparar no `baro_mic.py`.
- Se mostrar ~1 por segundo, o modo de 100 Hz não foi aceito: investigar `sensor_rate` (`0x2c0f04a0`) ou
  o modo de registro de dados do processador de sensores (`[algo_sampling_start] ... baro:%u`,
  `[algo_samsung_control_baro] ord:%u`).
- Se a pressão aparecer como "formato ?", o registro não é um `float` em hPa: as duas palavras cruas na
  tela e os registros salvos no arquivo dizem o formato real.

Mexer no firmware do processador de sensores não está nos planos: o fit3-toolkit não modifica nem
emula esse processador, e um erro ali pode afetar a detecção de queda.
