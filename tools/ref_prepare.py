#!/usr/bin/env python
"""Подготовка рефа из кандидата (gen_selected/*.mp3) -> in_progress/*.wav.

ПАЙПЛАЙН (по фидбэку 2026-09-03):
  1. Конвертация в WAV 24 kHz mono (16 bit).
  2. Анализ тишины (RMS-окна 20 мс, порог -45 dBFS).
  3. СЖАТИЕ ПАУЗ: пауза длиннее MAX_PAUSE (0.7 с) обрезается до
     TARGET_PAUSE (0.35 с) — слишком длинные паузы в рефе недопустимы
     (CV3 клонирует их ритм).
  4. Вырезка контента: от начала звука (первый не-тихий сэмпл) окно
     REF_LEN (10 с), хвост TAIL (0.15 с) тишины в конце.
  5. Выравнивание громкости: two-pass linear loudnorm (EBU R128)
     LOUD_I (-16 LUFS) / LOUD_TP (-1.5 dB) — ЕДИНЫЙ стандарт рефов
     проекта (все рефы в одной громкости).

ИСПОЛЬЗОВАНИЕ:
  python tools/ref_prepare.py --file "voice_candidates/{Имя}/gen_selected/{N}.mp3" \
      --char "Captain Belmont" [--variant 04]
  -> voice_candidates/{Имя}/in_progress/{Имя}[_{variant}].wav

Зависимости: system python + numpy + ffmpeg.
"""

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voicekit import paths  # noqa: E402

# ---- константы (единый стандарт, НЕ менять по файлам) ----
SR = 24000
WIN = 0.02             # окно анализа тишины, с
SILENCE_DB = -45.0     # порог тишины, dBFS (по RMS окна)
MAX_PAUSE = 0.7        # паузы длиннее — сжимаем, с
TARGET_PAUSE = 0.35    # целевая длина паузы после сжатия, с
TAIL = 0.15            # хвост тишины в конце окна, с
REF_LEN = 10.0         # целевая длина рефа, с
LOUD_I = -16.0         # EBU R128 integrated loudness, LUFS
LOUD_TP = -1.5         # true peak, dB
LOUD_LRA = 11.0

FFMPEG = 'ffmpeg'
FFPROBE = 'ffprobe'


def to_wav(src, dst):
    subprocess.run([FFMPEG, '-y', '-i', src, '-ac', '1', '-ar', str(SR),
                    '-sample_fmt', 's16', dst], check=True, capture_output=True)


def read_wav(path):
    import wave
    with wave.open(path, 'rb') as w:
        assert w.getframerate() == SR and w.getnchannels() == 1
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def write_wav(path, x):
    import wave
    data = (np.clip(x, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def compress_pauses(x):
    """Сжимаем паузы > MAX_PAUSE до TARGET_PAUSE. Возвращает (y, отчёт)."""
    n_win = max(int(WIN * SR), 1)
    frames = len(x) // n_win
    rms = np.sqrt(
        (x[:frames * n_win].reshape(frames, n_win) ** 2).mean(axis=1))
    thr = 10 ** (SILENCE_DB / 20)
    silent = rms < thr

    # границы сегментов: звук / пауза
    segs = []  # (is_silent, start_frame, end_frame)
    start = 0
    cur = silent[0]
    for i in range(1, frames):
        if silent[i] != cur:
            segs.append((cur, start, i))
            start = i
            cur = silent[i]
    segs.append((cur, start, frames))

    out = []
    max_pause_before = 0.0
    n_cut = 0
    for is_silent, a, b in segs:
        dur = (b - a) * WIN
        if not is_silent:
            out.append(x[a * n_win:b * n_win])
            continue
        if dur > max_pause_before:
            max_pause_before = dur
        if dur > MAX_PAUSE:
            keep = min(int(TARGET_PAUSE * SR / n_win), b - a)
            out.append(x[a * n_win:(a + keep) * n_win])
            n_cut += 1
        else:
            out.append(x[a * n_win:b * n_win])
    y = np.concatenate(out) if out else x[:0]
    return y, dict(max_pause_before=round(max_pause_before, 2),
                   pauses_cut=n_cut)


def strip_edges(seg):
    """Срезать тишину в начале и конце сегмента (окна 5мс, тот же порог).

    Звук = серия из >= 2 блоков выше порога (одиночный щелчок/всплеск
    не считается). Хвост: +20мс запаса после последнего звука.
    """
    n2 = max(int(0.005 * SR), 1)
    nfr = len(seg) // n2
    if nfr < 4:
        return seg
    rms = np.sqrt((seg[:nfr * n2].reshape(nfr, n2) ** 2).mean(axis=1))
    thr = 10 ** (SILENCE_DB / 20)
    mask = rms >= thr
    run = mask[:-1] & mask[1:]
    vi = np.where(run)[0]
    if len(vi) == 0:
        return seg[:0]
    s2 = vi[0] * n2
    e2 = min(len(seg), (vi[-1] + 2) * n2 + int(0.020 * SR))
    return seg[s2:e2]


def cut_content(x):
    """Окно ~10с, стартующее С ТИШИНЫ исходника (начало фразы).

    1. Размечаем тишину (окна 20мс, порог -45 dBFS).
    2. Кандидаты старта: 0 и НАЧАЛА каждой тишины (>= 0.15с) — так окно
       начинается с настоящей паузы/тишины, затем звук нарастает.
    3. Для каждого кандидата считаем конец: ближайшая пауза >= 0.2с в
       диапазоне [start+9, start+11]с, иначе конец звука + TAIL, иначе
       жёсткий start+10с (fade-out).
    4. Выбираем кандидата с длиной окна ближайшей к 10с (в приоритете
       те, что начинаются с тишины).
    """
    n_win = max(int(WIN * SR), 1)
    frames = len(x) // n_win
    rms = np.sqrt(
        (x[:frames * n_win].reshape(frames, n_win) ** 2).mean(axis=1))
    thr = 10 ** (SILENCE_DB / 20)
    silent = rms < thr
    voiced = np.where(~silent)[0]
    if len(voiced) == 0:
        return x, 0.0, len(x) / SR
    last_voiced = (voiced[-1] + 1) * n_win

    # начала тишины >= 0.15с
    starts = [0]
    i = 0
    while i < len(silent):
        if silent[i]:
            j = i
            while j < len(silent) and silent[j]:
                j += 1
            if (j - i) * WIN >= 0.15:
                starts.append(i * n_win)
            i = j
        else:
            i += 1

    def window_end(s):
        """(end, kind): kind = 'pause' | 'material' | 'hard'."""
        end = s + int(REF_LEN * SR)
        kind = 'hard'
        lo = min(s + int(9.0 * SR), len(x))
        hi = min(s + int(11.0 * SR), len(x))
        k = lo // n_win
        j = hi // n_win
        while k < j:
            if silent[k]:
                kk = k
                while kk < j and silent[kk]:
                    kk += 1
                if (kk - k) * WIN >= 0.2:
                    end = k * n_win + int(TAIL * SR)
                    kind = 'pause'
                    break
                k = kk
            else:
                k += 1
        end = min(end, len(x))
        if end == len(x) or end > last_voiced + int(TAIL * SR):
            if end > last_voiced + int(TAIL * SR):
                end = last_voiced + int(TAIL * SR)
            kind = 'material'
        return end, kind

    cands = []
    for s in starts:
        e, kind = window_end(s)
        dur = (e - s) / SR
        if dur <= 0:
            continue
        natural = kind != 'hard'
        cands.append((abs(dur - REF_LEN) + (0.0 if natural else 1.0),
                      s, e, dur, s > 0, natural))

    if cands:
        # приоритет: старт с тишины (8.5-11.5с); внутри — естественный
        # конец (пауза/конец материала) важнее точности 10с
        pool = [c for c in cands if c[4] and 8.5 <= c[3] <= 11.5]
        if not pool:
            pool = cands
        pool.sort(key=lambda c: (0 if c[5] else 1, c[0]))
        _, s, e, dur, _, _ = pool[0]
        seg = strip_edges(x[s:e])
        fo = min(len(seg), int(0.010 * SR))
        if fo:
            seg[-fo:] *= np.linspace(1.0, 0.0, fo)
        return seg, 0.0, len(seg) / SR
    return x, 0.0, len(x) / SR


def loudnorm_measure(path):
    p = subprocess.run(
        [FFMPEG, '-i', path, '-af',
         'loudnorm=I={}:TP={}:LRA={}:print_format=json'.format(
             LOUD_I, LOUD_TP, LOUD_LRA),
         '-f', 'null', '-'], capture_output=True, text=True)
    m = re.search(r'\{.*\}', p.stderr, re.S)
    return json.loads(m.group(0)) if m else {}


def loudnorm_apply(src, dst, meas):
    args = ('loudnorm=I={}:TP={}:LRA={}:measured_I={}:measured_TP={}'
            ':measured_LRA={}:measured_thresh={}:offset={}:linear=true').format(
        LOUD_I, LOUD_TP, LOUD_LRA, meas['input_i'], meas['input_tp'],
        meas['input_lra'], meas['input_thresh'], meas['target_offset'])
    subprocess.run([FFMPEG, '-y', '-i', src, '-af', args,
                    '-ac', '1', '-ar', str(SR), dst],
                   check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser(description='Подготовка рефа из кандидата')
    ap.add_argument('--file', required=True, help='исходный mp3/wav')
    ap.add_argument('--char', required=True, help='имя персонажа (папка)')
    ap.add_argument('--variant', default='',
                    help='суффикс варианта (04 -> {Name}_04.wav)')
    args = ap.parse_args()

    tmp = os.path.join(paths.OUTPUT_DIR, 'voice', '_ref_prepare_tmp.wav')
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    to_wav(args.file, tmp)
    x = read_wav(tmp)

    y, report = compress_pauses(x)
    y, start_s, dur = cut_content(y)

    suffix = '_{}'.format(args.variant) if args.variant else ''
    out = os.path.join(paths.char_subdir(args.char, 'in_progress'),
                       args.char + suffix + '.wav')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_wav(out, y)

    meas = loudnorm_measure(out)
    loudnorm_apply(out, out + '.ln.wav', meas)
    os.replace(out + '.ln.wav', out)

    meas2 = loudnorm_measure(out)
    print('исходник: {:.1f}s'.format(len(x) / SR))
    print('паузы: макс. {:.1f}s до, сжато {} пауз (>{}с -> {:.1f}s)'.format(
        report['max_pause_before'], report['pauses_cut'],
        MAX_PAUSE, TARGET_PAUSE))
    print('окно: старт {:.2f}s, длительность {:.2f}s (цель {:.0f}s)'.format(
        start_s, dur, REF_LEN))
    print('громкость: {:.1f} LUFS / TP {:.1f} (стандарт {} / {})'.format(
        float(meas2.get('input_i', -99)), float(meas2.get('input_tp', -99)),
        LOUD_I, LOUD_TP))
    print('-> {}'.format(os.path.relpath(out, paths.ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())