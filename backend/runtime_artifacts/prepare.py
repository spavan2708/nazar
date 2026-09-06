"""Package explicitly allowlisted existing files, without importing ML libraries."""
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from download import digest, verify_file, run

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'runtime-artifacts-2026-09-06.1'
EMBEDDING = 'ml/artifacts/embedding_model/'
GROUPS = {
    'nazar-minilm.tar.gz': [EMBEDDING + name for name in (
        '1_Pooling/config.json', 'README.md', 'config.json',
        'config_sentence_transformers.json', 'model.safetensors', 'modules.json',
        'sentence_bert_config.json', 'tokenizer.json', 'tokenizer_config.json')],
    'nazar-classifiers.tar.gz': ['ml/artifacts/classifier.joblib', 'ml/artifacts/metadata.json',
                               'ml/artifacts/v2/classifier.joblib', 'ml/artifacts/v2/metadata.json'],
    'nazar-whisper.tar.gz': ['stt/models/ggml-base.bin'],
}
PINNED = {
    EMBEDDING + 'model.safetensors': '7f4f89d628f87ade0e0b57c40affb6402cd77abc8110584d8d35dc86da514ee8',
    'stt/models/ggml-base.bin': '60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe',
}


def main():
    output = ROOT / '.runtime-artifacts' / VERSION
    manifest_path = Path(__file__).with_name('manifest.json')
    if output.exists() or manifest_path.exists():
        raise ValueError('Refusing to overwrite an existing artifact version or manifest')
    actual = {str(p.relative_to(ROOT)) for p in (ROOT / EMBEDDING).rglob('*') if not p.is_dir()}
    if actual != set(GROUPS['nazar-minilm.tar.gz']):
        raise ValueError('Unexpected MiniLM directory contents')
    manifest = dict(schema_version=1, artifact_version=VERSION, repository='spavan2708/nazar',
                    source_git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    destination_root='backend/', archives=[])
    for name, paths in GROUPS.items():
        files = []
        for relative in paths:
            path = ROOT / relative
            if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
                raise ValueError(f'Nonregular source: {relative}')
            record = dict(path=relative, size_bytes=path.stat().st_size, sha256=digest(path))
            if relative in PINNED and record['sha256'] != PINNED[relative]:
                raise ValueError('Production model hash mismatch')
            files.append(record)
        manifest['archives'].append(dict(name=name, url=None, files=files))
    output.mkdir(parents=True)
    for bundle in manifest['archives']:
        archive = output / bundle['name']
        with archive.open('xb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                for record in bundle['files']:
                    path = ROOT / record['path']
                    verify_file(path, record)
                    info = tarfile.TarInfo(record['path'])
                    info.size = record['size_bytes']
                    info.mode = 0o644
                    with path.open('rb') as source:
                        tar.addfile(info, source)
                    verify_file(path, record)
        bundle.update(size_bytes=archive.stat().st_size, sha256=digest(archive))
    with tempfile.TemporaryDirectory(prefix='nazar-package-check-') as scratch:
        candidate = Path(scratch) / 'manifest.json'
        candidate.write_text(json.dumps(manifest))
        run(candidate, Path(scratch) / 'restored', output)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    for bundle in manifest['archives']:
        print(bundle['name'], bundle['size_bytes'], bundle['sha256'])


if __name__ == '__main__':
    main()
