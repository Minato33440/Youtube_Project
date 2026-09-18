import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8-sig'))
files = [p for p in root.iterdir() if p.is_file() and p.suffix in {'.png', '.psd', '.json', '.md', '.js', '.py'}]
files += [root / layer['path'] for layer in manifest['layers']]
files += list((root / 'generated').glob('*.png'))
files += [p for p in (root / 'tools').iterdir() if p.is_file()]
model = root / 'Risa_Live2D_Parts_v1_import_check.cmo3'
assert model.exists(), 'Import check model must be saved first'
files.append(model)
target = root / 'Risa_Live2D_Parts_v1_bundle.zip'
with ZipFile(target, 'w', ZIP_DEFLATED) as archive:
    for file in sorted(set(files)):
        archive.write(file, file.relative_to(root).as_posix())
with ZipFile(target) as archive:
    assert archive.testzip() is None
    assert len([n for n in archive.namelist() if n.startswith('parts/')]) == 23
print(json.dumps({'zip': str(target), 'files': len(files), 'bytes': target.stat().st_size, 'crc': 'pass'}, ensure_ascii=False))
