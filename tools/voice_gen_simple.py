#!/usr/bin/env python
"""Simple voice generator wrapper - uses cosyvoice3_demo.py + audio_trim.py."""

import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description='TSSR Voice Generator (simple wrapper)')
    parser.add_argument('--text', required=True, help='text to generate')
    parser.add_argument('--ref', required=True, help='reference voice path')
    parser.add_argument('--out', required=True, help='output path')
    parser.add_argument('--id', default=None, help='translation ID')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--no-trim', action='store_true', help='skip trimming')
    args = parser.parse_args()
    
    # Generate with cosyvoice3_demo.py
    demo_script = r'C:\Users\Domo\AppData\LocalLow\Owlcat Games\Warhammer 40000 Rogue Trader\UnityModManager\W40KRTAudioDirectMod\tools\cosyvoice3_demo.py'
    
    cmd = [
        r'C:\tools\cosyvoice3\.venv\Scripts\python.exe',
        demo_script,
        '--text', args.text,
        '--ref', args.ref,
        '--out', args.out,
        '--mode', 'cross_lingual',
        '--tail-trim',
        '--s16',
        '--seed', str(args.seed),
        '--lang-token', 'ru',
    ]
    
    print('Generating:', args.text[:50])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('ERROR:', result.stderr)
        return 1
    
    print('Generated:', args.out)
    
    # Post-process with trim_tail_burst.py (pattern: gap + short burst at EOF)
    if not args.no_trim:
        trim_script = os.path.join(os.path.dirname(__file__), 'trim_tail_burst.py')

        cmd = [
            r'C:\tools\cosyvoice3\.venv\Scripts\python.exe',
            trim_script,
            args.out,
            '--in-place',
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print('Trim failed:', result.stderr)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
