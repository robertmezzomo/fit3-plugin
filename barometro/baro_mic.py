#!/usr/bin/env python3
"""baro_mic.py: turns a stream of barometric pressure samples into audio ("barometer as a microphone").

Proof of concept. A wrist barometer such as the Fit3's ST LPS27HHTW samples at most ~200 Hz, so only
frequencies below ~100 Hz can be present in its data; voice intelligibility lives at 300-3400 Hz.
This pipeline extracts whatever acoustic energy survives in the usable band, suppresses the sensor's
noise floor, and renders the result as a 16 kHz WAV.

Input:  CSV with one pressure value per line (hPa or Pa, see --unit), optionally "t,pressure".
Output: 16 kHz mono 16-bit WAV.

    python3 baro_mic.py samples.csv --fs 200 -o out.wav

Pipeline:
  1. units to Pa, remove the mean
  2. high-pass (default 15 Hz): removes weather, altitude changes and arm movements (raising the
     wrist 10 cm changes the pressure by ~1.2 Pa, more than speech near the mouth)
  3. low-pass just under Nyquist (default 0.45 * fs)
  4. spectral gating: estimates the noise floor from the quietest frames and attenuates bins that
     do not rise above it (a classic noise-reduction step for stationary noise)
  5. normalisation, then resampling to 16 kHz for playback
"""
import argparse
import csv
import sys
import wave

import numpy as np
from scipy import signal

OUT_RATE = 16000


def load_csv(path, unit):
    vals = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                vals.append(float(row[-1]))
            except ValueError:
                continue  # header
    x = np.asarray(vals, dtype=np.float64)
    return x * 100.0 if unit == "hPa" else x


def bandpass(x, fs, lo, hi):
    hi = min(hi, 0.49 * fs)
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x)


def spectral_gate(x, fs, frame_s=0.16, noise_quantile=0.15, over=1.5, floor=0.08):
    """Attenuates time-frequency bins that stay under the estimated noise floor."""
    nper = max(16, int(frame_s * fs))
    f, t, Z = signal.stft(x, fs=fs, nperseg=nper, noverlap=nper * 3 // 4)
    mag = np.abs(Z)
    energy = (mag ** 2).sum(axis=0)
    quiet = energy <= np.quantile(energy, noise_quantile)
    noise = mag[:, quiet].mean(axis=1, keepdims=True) if quiet.any() else np.median(mag, axis=1, keepdims=True)
    gain = np.clip((mag - over * noise) / np.maximum(mag, 1e-12), floor, 1.0)
    gain = signal.medfilt2d(gain, kernel_size=(3, 5))  # smooths musical noise
    _, y = signal.istft(Z * gain, fs=fs, nperseg=nper, noverlap=nper * 3 // 4)
    return y[: len(x)]


def process(pa, fs, hp=15.0, lp=None, gate=True):
    """pressure samples in Pa at fs Hz -> cleaned signal at fs Hz (arbitrary units)"""
    x = pa - np.mean(pa)
    x = bandpass(x, fs, hp, lp if lp else 0.45 * fs)
    if gate:
        x = spectral_gate(x, fs)
    return x


def to_audio(y, fs, peak=0.9):
    up = signal.resample_poly(y, OUT_RATE, int(round(fs)))
    m = np.max(np.abs(up))
    return up * (peak / m) if m > 0 else up


def write_wav(path, audio, rate=OUT_RATE):
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv")
    ap.add_argument("--fs", type=float, required=True, help="sample rate of the pressure data (Hz)")
    ap.add_argument("--unit", choices=["hPa", "Pa"], default="hPa")
    ap.add_argument("--hp", type=float, default=15.0, help="high-pass cut-off (Hz)")
    ap.add_argument("--lp", type=float, default=None, help="low-pass cut-off (Hz), default 0.45*fs")
    ap.add_argument("--no-gate", action="store_true", help="skip spectral noise gating")
    ap.add_argument("-o", "--out", default="baro_mic.wav")
    a = ap.parse_args(argv)
    pa = load_csv(a.csv, a.unit)
    if len(pa) < a.fs:
        sys.exit("need at least one second of samples")
    y = process(pa, a.fs, a.hp, a.lp, not a.no_gate)
    write_wav(a.out, to_audio(y, a.fs))
    print("wrote %s (%.1f s, usable band %.0f-%.0f Hz)" % (a.out, len(pa) / a.fs, a.hp, a.lp or 0.45 * a.fs))


if __name__ == "__main__":
    main()
