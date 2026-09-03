"""Тесты ref_prepare: сжатие пауз и вырезка окна."""

import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import ref_prepare as rp  # noqa: E402


def test_compress_pauses_cuts_long():
    """Пауза > MAX_PAUSE сжимается до TARGET_PAUSE."""
    sr = rp.SR
    # тон 1с + пауза 2с + тон 1с
    tone = np.sin(2 * np.pi * 220 * np.arange(sr) / sr) * 0.3
    pause = np.zeros(2 * sr)
    x = np.concatenate([tone, pause, tone])
    y, rep = rp.compress_pauses(x)
    assert rep['pauses_cut'] == 1
    assert rep['max_pause_before'] >= 2.0
    assert len(y) / sr < 3.5  # 1 + 0.35 + 1
    assert len(y) / sr > 2.0


def test_compress_pauses_keeps_short():
    """Короткая пауза (0.3с) не трогается."""
    sr = rp.SR
    tone = np.sin(2 * np.pi * 220 * np.arange(sr) / sr) * 0.3
    pause = np.zeros(int(0.3 * sr))
    x = np.concatenate([tone, pause, tone])
    y, rep = rp.compress_pauses(x)
    assert rep['pauses_cut'] == 0
    assert abs(len(y) / sr - 2.3) < 0.1


def test_cut_content_window():
    """Непрерывный звук: жёсткое окно 10с от старта."""
    sr = rp.SR
    tone = np.sin(2 * np.pi * 220 * np.arange(int(20 * sr)) / sr) * 0.3
    y, start, dur = rp.cut_content(tone)
    assert start == 0.0
    assert abs(dur - rp.REF_LEN) < 0.05
    assert abs(len(y) / sr - rp.REF_LEN) < 0.05


def test_cut_content_starts_at_silence():
    """Старт с тишины исходника: фраза после паузы (~9.5с звука)."""
    sr = rp.SR
    tone1 = np.sin(2 * np.pi * 220 * np.arange(int(2 * sr)) / sr) * 0.3
    pause = np.zeros(int(0.5 * sr))
    tone2 = np.sin(2 * np.pi * 220 * np.arange(int(9.5 * sr)) / sr) * 0.3
    tail = np.zeros(int(1.0 * sr))
    x = np.concatenate([tone1, pause, tone2, tail])
    y, start, dur = rp.cut_content(x)
    assert start == 0.0          # тишина по краям срезана
    assert abs(dur - 9.65) < 0.15   # 2.5..12.15: звук 9.5 + хвост 0.15
    assert abs(len(y) / sr - 9.65) < 0.15
    assert np.abs(y[:100]).max() > 0.1   # начинается сразу со звука


def test_cut_content_short_keeps_tail():
    """Короткий звук с тишиной в конце: целиком + хвост TAIL."""
    sr = rp.SR
    tone = np.sin(2 * np.pi * 220 * np.arange(int(3 * sr)) / sr) * 0.3
    tail = np.zeros(int(1.0 * sr))
    x = np.concatenate([tone, tail])
    y, start, dur = rp.cut_content(x)
    assert start == 0.0
    assert abs(dur - 3.02) < 0.1   # звук 3с + запас 20мс