#!/usr/bin/env python3
"""simulate_fit3_baro.py: what would the Fit3's barometer "hear" of a voice?

Feeds a speech recording through a model of the wrist barometer and through baro_mic.py, and
writes WAV files to listen to plus a few numbers. No watch needed: this answers the question
before anyone reverse-engineers the sensor hub to stream raw pressure.

    python3 simulate_fit3_baro.py --text "Oi, estou chegando" -o resultados/
    python3 simulate_fit3_baro.py --wav minha_voz.wav --spl 85 -o resultados/

Sensor model (ST LPS27HHTW, the barometer named in the Fit3 sensor-hub firmware; the GMP108 and
MSPC110 drivers are there too). Values are datasheet-class figures, not measurements of a Fit3:
  * output data rate: up to 200 Hz (--odr)
  * each sample is the average of the pressure over its conversion window (--avg, fraction of the
    sample period; 0 = instantaneous sample-and-hold, which aliases high frequencies down instead
    of removing them: the best case for recovering anything)
  * noise: ~0.7 Pa RMS (--noise)
  * resolution: 1/4096 hPa (0.024 Pa)
Sound pressure: 94 dB SPL = 1 Pa RMS. Speech is ~60 dB at 1 m, ~85 dB a few cm from the mouth.
"""
import argparse
import os
import subprocess
import tempfile
import wave

import numpy as np
from scipy import signal

import baro_mic

P_REF = 20e-6  # Pa


def read_wav(path):
    with wave.open(path) as w:
        fs, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype={1: np.uint8, 2: "<i2", 4: "<i4"}[sw]).astype(np.float64)
    if sw == 1:
        x -= 128
    x = x.reshape(-1, ch).mean(axis=1)
    return x / np.max(np.abs(x)), fs


def speak(text, voice):
    path = os.path.join(tempfile.mkdtemp(), "voz.wav")
    subprocess.run(["espeak-ng", "-v", voice, "-s", "150", "-w", path, text], check=True)
    return path


def active_rms(x, fs):
    """RMS over the frames where speech is present (the usual way to state a speech level)"""
    hop = int(0.02 * fs)
    fr = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    return np.sqrt(np.mean(fr[fr > 0.1 * fr.max()] ** 2))


def sensor(pa, fs, odr, avg, noise, rng):
    """pressure waveform (Pa, fs) -> barometer samples (Pa, odr)"""
    step = fs / odr
    win = max(1, int(round(avg * step)))
    smoothed = np.convolve(pa, np.ones(win) / win, mode="same") if win > 1 else pa
    idx = np.arange(0, len(pa), step).astype(int)
    s = smoothed[idx] + rng.normal(0, noise, len(idx))
    lsb = 100.0 / 4096.0  # 1/4096 hPa in Pa
    return np.round(s / lsb) * lsb


def envelope(x, fs, win=0.05):
    hop = max(1, int(win * fs))
    return np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop + 1, hop)])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--wav", help="a speech recording")
    src.add_argument("--text", help="text to synthesise with espeak-ng")
    ap.add_argument("--voice", default="pt-br")
    ap.add_argument("--spl", type=float, nargs="+", default=[94, 85, 70], help="speech level(s) at the watch, dB SPL")
    ap.add_argument("--odr", type=float, default=200)
    ap.add_argument("--avg", type=float, default=1.0)
    ap.add_argument("--noise", type=float, default=0.7, help="sensor noise, Pa RMS")
    ap.add_argument("-o", "--out", default="resultados")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(1)

    x, fs = read_wav(a.wav if a.wav else speak(a.text, a.voice))
    baro_mic.write_wav(os.path.join(a.out, "0_original.wav"), signal.resample_poly(x, 16000, fs) * 0.9)

    ideal = baro_mic.bandpass(x, fs, 15, 0.45 * a.odr)  # a perfect, noiseless 200 Hz "microphone"
    ideal_ds = signal.resample_poly(ideal, int(a.odr), fs)
    baro_mic.write_wav(os.path.join(a.out, "1_sensor_perfeito_sem_ruido.wav"), baro_mic.to_audio(ideal_ds, a.odr))

    env_ref = envelope(x, fs)
    print("banda que um sensor de %.0f Hz consegue ver: ate %.0f Hz" % (a.odr, a.odr / 2))
    print("energia da fala que cai nessa banda: %.2f%%" % (100 * np.sum(ideal ** 2) / np.sum((x - x.mean()) ** 2)))
    print()
    print("%-8s %-12s %-14s %s" % ("dB SPL", "fala (Pa)", "SNR no sensor", "correlacao do envelope (depois do processamento)"))
    for spl in a.spl:
        pa = x * (P_REF * 10 ** (spl / 20) / active_rms(x, fs))
        raw = sensor(pa, fs, a.odr, a.avg, a.noise, rng)
        # what the speech alone and the noise alone contribute, in the band the pipeline keeps
        clean = sensor(pa, fs, a.odr, a.avg, 0.0, rng)
        sig_band = baro_mic.bandpass(clean - clean.mean(), a.odr, 15, 0.45 * a.odr)
        noise_band = baro_mic.bandpass(raw - clean, a.odr, 15, 0.45 * a.odr)
        snr_in = 10 * np.log10(np.mean(sig_band ** 2) / np.mean(noise_band ** 2))
        out = baro_mic.process(raw, a.odr)
        env_out = envelope(out, a.odr)
        n = min(len(env_ref), len(env_out))
        corr = np.corrcoef(env_ref[:n], env_out[:n])[0, 1]
        tag = "%ddB" % spl
        np.savetxt(os.path.join(a.out, "baro_%s.csv" % tag), raw / 100.0 + 1013.25, fmt="%.6f")
        baro_mic.write_wav(os.path.join(a.out, "2_sensor_cru_%s.wav" % tag), baro_mic.to_audio(raw - raw.mean(), a.odr))
        baro_mic.write_wav(os.path.join(a.out, "3_processado_%s.wav" % tag), baro_mic.to_audio(out, a.odr))
        print("%-8.0f %-12.3f %-14s %.2f" % (spl, P_REF * 10 ** (spl / 20), "%+.1f dB" % snr_in, corr))
    print()
    print("SNR: potencia da fala / potencia do ruido na banda util (0 dB = iguais).")
    print("correlacao do envelope: 1 = o volume do sinal acompanha a fala; ~0 = nao acompanha.")


if __name__ == "__main__":
    main()
