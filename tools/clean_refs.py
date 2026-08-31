#!/usr/bin/env python
"""Чистка рефов голосов: денойз + EQ + громкость (ffmpeg, без нейронок).

ПРОБЛЕМЫ ИСТОЧНИКОВ (обе решаем здесь):
  1. Лёгкое «подшипливание» (шум/яркость >8 кГц) — CV3 клонирует тембр
     вместе с шумом, поэтому чистим рефы ДО генерации.
  2. РАЗНАЯ ГРОМКОСТЬ рефов — голоса «гуляли» (где-то тихо, где-то громко),
     и генерация наследовала уровень. Выравниваем все рефы в один
     стандарт: EBU R128 loudnorm, цель -16 LUFS, TP -1.5 dB.

ЦЕПОЧКА ffmpeg (порядок важен):
  1. afftdn nr=15              — FFT-денойз (убирает равномерный шип)
  2. deesser i=0.5             — срез сибилянтов «с/ш» (i: 0..1)
  3. highshelf f=8000 g=-6     — приглушение яркости >8 кГц (фикс из W40KRT)
  4. loudnorm I=-16 (2 прохода) — выравнивание громкости (EBU R128)

ОРИГИНАЛЫ НЕ ТРОГАЕМ: читаем из одной папки, пишем в другую.

Запуск:
  python tools/clean_refs.py
  python tools/clean_refs.py --src refs/raw --dst refs/voices
"""

import argparse
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Цепочка фильтров чистки (до loudnorm; тот идёт вторым проходом)
FILTERS = 'afftdn=nr=15,deesser=i=0.5,highshelf=f=8000:g=-6'

# Параметры loudnorm: цель громкости и допустимый пик (EBU R128)
LOUD_I = -16.0   # интегральная громкость, LUFS
LOUD_TP = -1.5   # true peak, dB
LOUD_LRA = 11.0  # диапазон громкости


def loudnorm_two_pass(path, dst):
    """Выравнивание громкости в 2 прохода (анализ + применение).

    1-й проход: ffmpeg меряет вход (print_format=json в stderr).
    2-й проход: применяет с measured_*-параметрами (linear=true).
    """
    probe = subprocess.run(
        ['ffmpeg', '-i', path, '-af',
         'loudnorm=I={}:TP={}:LRA={}:print_format=json'.format(
             LOUD_I, LOUD_TP, LOUD_LRA),
         '-f', 'null', '-'],
        capture_output=True, text=True)
    m = re.search(r'\{.*\}', probe.stderr, re.S)
    if not m:
        raise RuntimeError('loudnorm probe: нет json в выводе ffmpeg')
    d = json.loads(m.group(0))
    args = ('loudnorm=I={}:TP={}:LRA={}:measured_I={}:measured_TP={}:'
            'measured_LRA={}:measured_thresh={}:linear=true'.format(
                LOUD_I, LOUD_TP, LOUD_LRA,
                d['input_i'], d['input_tp'], d['input_lra'], d['input_thresh']))
    tmp = dst + '.tmp.wav'
    subprocess.run(['ffmpeg', '-y', '-i', path, '-af', args,
                    '-ac', '1', '-ar', '24000', tmp],
                   check=True, capture_output=True)
    os.replace(tmp, dst)


def clean_file(src, dst):
    """Один WAV: чистка (денойз+EQ) -> loudnorm. True если обработан."""
    if os.path.exists(dst):
        return False  # уже чищеный — не трогаем
    tmp = dst + '.tmp1.wav'
    subprocess.run(['ffmpeg', '-y', '-i', src, '-af', FILTERS,
                    '-ac', '1', '-ar', '24000', tmp],
                   check=True, capture_output=True)
    loudnorm_two_pass(tmp, dst)
    os.remove(tmp)
    return True


def main():
    ap = argparse.ArgumentParser(description='Чистка рефов голосов (ffmpeg)')
    ap.add_argument('--src', default=os.path.join(ROOT, 'refs', 'raw'))
    ap.add_argument('--dst', default=os.path.join(ROOT, 'refs', 'voices'))
    ap.add_argument('--force', action='store_true', help='пересобрать существующие')
    args = ap.parse_args()

    os.makedirs(args.dst, exist_ok=True)
    files = sorted(f for f in os.listdir(args.src) if f.endswith('.wav'))
    print('фильтры: {}'.format(FILTERS))
    for f in files:
        src = os.path.join(args.src, f)
        dst = os.path.join(args.dst, f)
        if args.force and os.path.exists(dst):
            os.remove(dst)
        made = clean_file(src, dst)
        print('  {:<28s} {}'.format(f, 'OK' if made else 'skip (уже есть)'))
        # txt-транскрипт копируем рядом (нужен zero_shot, не трогаем содержимое)
        txt_src = src[:-4] + '.txt'
        txt_dst = dst[:-4] + '.txt'
        if os.path.exists(txt_src) and not os.path.exists(txt_dst):
            with open(txt_src, 'rb') as a, open(txt_dst, 'wb') as b:
                b.write(a.read())
    print('готово: {} -> {}'.format(args.src, args.dst))


if __name__ == '__main__':
    main()
