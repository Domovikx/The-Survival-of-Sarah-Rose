#!/usr/bin/env python
"""Чистка рефов голосов: денойз + EQ + громкость (ffmpeg, без нейронок).

ПРОБЛЕМЫ ИСТОЧНИКОВ (обе решаем здесь):
  1. Лёгкое «подшипливание» (шум/яркость >8 кГц) — CV3 клонирует тембр
     вместе с шумом, поэтому чистим рефы ДО генерации.
  2. РАЗНАЯ ГРОМКОСТЬ рефов — голоса «гуляли» (где-то тихо, где-то громко),
     и генерация наследовала уровень. Выравниваем все рефы в один
     стандарт: EBU R128 loudnorm, цель -16 LUFS, TP -1.5 dB.

ЦЕПОЧКА ffmpeg (порядок важен):
  1. highpass f=60            — срез низкочастотного гула/постоянки
  2. afftdn nr=15              — FFT-денойз (убирает равномерный шип)
  3. deesser i=0.5             — срез сибилянтов «с/ш» (i: 0..1)
  4. highshelf f=8000 g=-6     — приглушение яркости >8 кГц (фикс из W40KRT)
  5. loudnorm I=-16 (2 прохода) — выравнивание громкости (EBU R128)
  6. afade in/out 30мс        — защита от кликов по краям

ПО УМОЛЧАНИЮ IN-PLACE: refs/ -> refs/, существующие скипаются.
Пересборка: --force. Или отдельные папки --src/--dst.

Запуск:
  python tools/clean_refs.py
  python tools/clean_refs.py --force
"""

import argparse
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Цепочка фильтров чистки (до loudnorm; тот идёт вторым проходом)
FILTERS = 'highpass=f=60,afftdn=nr=15,deesser=i=0.5,highshelf=f=8000:g=-6'

# Фейды по краям (защита от кликов/щелчков)
FADE = 0.03   # 30 мс в начале и в конце

# Длина рефа (для расчёта точки старта fade-out)
TARGET_LEN = 10.0

# Параметры loudnorm: цель громкости и допустимый пик (EBU R128)
LOUD_I = -16.0   # интегральная громкость, LUFS
LOUD_TP = -1.5   # true peak, dB
LOUD_LRA = 11.0  # диапазон громкости


def loudnorm_two_pass(path, dst):
    """Выравнивание громкости в 2 прохода (анализ + применение).

    1-й проход: ffmpeg меряет вход (print_format=json в stderr).
    2-й проход: применяет с measured_*-параметрами.
    linear=false (ДИНАМИЧЕСКИЙ режим): loudnorm сам жмёт/растягивает динамику
    к LRA-цели, поэтому ВСЕ рефы сходятся к -16 LUFS вплотную (±0.5),
    даже тихие с редкими пиками (у них linear-режим упирался в TP-лимит
    и давал разброс -15...-19).
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
            'measured_LRA={}:measured_thresh={}:linear=false'.format(
                LOUD_I, LOUD_TP, LOUD_LRA,
                d['input_i'], d['input_tp'], d['input_lra'], d['input_thresh']))
    tmp = dst + '.tmp.wav'
    subprocess.run(['ffmpeg', '-y', '-i', path, '-af', args,
                    '-ac', '1', '-ar', '24000', tmp],
                   check=True, capture_output=True)
    os.replace(tmp, dst)


def clean_file(src, dst, force=False):
    """Один WAV: чистка (денойз+EQ) -> loudnorm -> фейды. True если обработан.

    force=False: существующий dst не трогаем.
    force=True: пересобираем. При in-place (src == dst) копии не нужны —
    src читается ffmpeg'ом только в начале, поэтому писать поверх безопасно.
    """
    if os.path.exists(dst) and not force:
        return False  # уже чищеный — не трогаем
    tmp = dst + '.tmp1.wav'
    subprocess.run(['ffmpeg', '-y', '-i', src, '-af', FILTERS,
                    '-ac', '1', '-ar', '24000', tmp],
                   check=True, capture_output=True)
    loudnorm_two_pass(tmp, dst)
    os.remove(tmp)
    # Фейды по краям (30мс) — глушим клики.
    # st рассчитываем от РЕАЛЬНОЙ длительности (клип может быть короче 10с).
    dur = float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', dst]).decode().strip().splitlines()[0])
    st_out = max(0.0, dur - FADE)
    tmp_fade = dst + '.tmp2.wav'
    subprocess.run(['ffmpeg', '-y', '-i', dst,
                    '-af', 'afade=t=in:d={},afade=t=out:st={:.3f}:d={}'.format(
                        FADE, st_out, FADE),
                    '-ac', '1', '-ar', '24000', tmp_fade],
                   check=True, capture_output=True)
    os.replace(tmp_fade, dst)
    return True


def main():
    ap = argparse.ArgumentParser(
        description='Чистка рефов голосов (ffmpeg). По умолчанию in-place:'
                    ' refs/ -> refs/ (без --force существующие скипаются).')
    ap.add_argument('--src', default=os.path.join(ROOT, 'refs'))
    ap.add_argument('--dst', default=os.path.join(ROOT, 'refs'))
    ap.add_argument('--force', action='store_true', help='пересобрать существующие')
    args = ap.parse_args()

    if os.path.abspath(args.src) != os.path.abspath(args.dst):
        os.makedirs(args.dst, exist_ok=True)
    files = sorted(f for f in os.listdir(args.src) if f.endswith('.wav'))
    print('фильтры: {}'.format(FILTERS))
    for f in files:
        src = os.path.join(args.src, f)
        dst = os.path.join(args.dst, f)
        made = clean_file(src, dst, force=args.force)
        print('  {:<28s} {}'.format(f, 'OK' if made else 'skip (уже есть)'))
    print('готово: {} -> {}'.format(args.src, args.dst))


if __name__ == '__main__':
    main()
