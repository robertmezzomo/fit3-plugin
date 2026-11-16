# Fit3 Voz — receptor das gravações

Página que roda no navegador (inclusive no celular, sem instalar nada) para **ouvir e avaliar a
qualidade** das gravações do sensor do relógio. Você exporta o arquivo pelo gerenciador de arquivos do
Fit3 App e abre na página.

Publicada em: https://claude.ai/artifact/AeyQ7QF5kiJ3e8febdW99K

## O que faz

- Lê `accel.bin` (app Acelerometro), `baro.bin` (app Barometro) e o formato `F3R1` do gravador futuro.
- Mostra **forma de onda**, **espectrograma** e **métricas**: banda captada, relação sinal/ruído,
  energia na faixa da voz (300–3400 Hz) e um veredito em texto.
- Deixa escolher o eixo (X/Y/Z/módulo), a taxa em Hz, filtros de grave/agudo, redução de chiado e um
  controle para acelerar/agudizar e tentar entender melhor a fala.
- **Toca** o áudio (reamostrado para 16 kHz). Tudo acontece no navegador; nada é enviado.

## Limites

- A página **não salva** um arquivo WAV: o sandbox de páginas hospedadas bloqueia downloads. Ouvir e
  analisar funciona; o salvar/enviar fica para o app do celular.
- O `accel.bin` do app de teste atual **não grava a taxa junto**, então você informa em Hz a maior taxa
  que o teste mediu. O gravador definitivo (formato `F3R1`) grava a taxa e dispensa isso.
