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

## Para captar no relógio de verdade (ainda não feito)

1. **Achar como pedir leituras cruas ao processador de sensores.** O firmware dele tem um modo de
   registro de dados (`[algo_sampling_start] acce:%u, gyro:%u, baro:%u, ...` e cabeçalhos CSV como
   `count,ts,acc_x,...,baro,hr,als`) e o comando `[algo_samsung_control_baro] ord:%u`, que ajusta a
   taxa do barômetro. Ainda é preciso descobrir como o processador principal aciona esse modo.
2. **Um mini-app `.f3x`** no Application Hub que pede esse modo, grava as leituras num arquivo em
   `/user` e permite puxar o arquivo por Bluetooth.
3. **Passar o arquivo pelo `baro_mic.py`**.

Mexer no firmware do processador de sensores não está nos planos: o fit3-toolkit não modifica nem
emula esse processador, e um erro ali pode afetar a detecção de queda.
