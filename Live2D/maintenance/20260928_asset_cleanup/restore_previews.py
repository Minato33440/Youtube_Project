"""Preview restoration is dry-run unless --apply is supplied. Never overwrites."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
LIVE = (ROOT / 'Live2D').resolve()
PROTECTED = (LIVE / 'Traning').resolve()


def checked(relative):
    p = (ROOT / relative).resolve()
    if not p.is_relative_to(LIVE) or p.is_relative_to(PROTECTED):
        raise ValueError(relative)
    return p


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    moves = json.loads(Path(__file__).with_name('movement_manifest.json').read_text('utf-8'))['moves']
    pending = []
    for row in moves:
        src, dest = checked(row['destination']), checked(row['source'])
        if dest.exists():
            print('SKIP existing destination:', row['source'])
            continue
        if not src.is_file() or sha(src) != row['sha256']:
            raise ValueError('Missing or changed archive: ' + row['destination'])
        pending.append((src, dest, row['sha256']))
    for src, dest, expected in pending:
        if args.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            src.replace(dest)
            if sha(dest) != expected:
                raise ValueError('Restore hash mismatch')
    print(('Restored' if args.apply else 'Would restore'), len(pending), 'files; no overwrite; no Traning changes.')


if __name__ == '__main__':
    main()
