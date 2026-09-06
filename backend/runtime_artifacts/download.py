"""Fetch pinned release archives and restore only verified, allowlisted bytes."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import urlopen


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify_file(path, record):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Missing or nonregular file: {path.name}')
    if path.stat().st_size != record['size_bytes'] or digest(path) != record['sha256']:
        raise ValueError(f'Integrity mismatch: {path.name}')


def restore(archive, bundle, destination):
    verify_file(archive, bundle)
    allowed = {f['path']: f for f in bundle['files']}
    if len(allowed) != len(bundle['files']):
        raise ValueError('Duplicate manifest paths')
    for name in allowed:
        p = PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or str(p) != name:
            raise ValueError('Unsafe manifest path')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or set(names) != set(allowed):
            raise ValueError('Archive path allowlist mismatch')
        if any(not m.isfile() or m.size != allowed[m.name]['size_bytes'] for m in members):
            raise ValueError('Nonregular member or incorrect size')
        # Never use extractall: links and archive-controlled filesystem metadata are rejected.
        for member in members:
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
            verify_file(target, allowed[member.name])


def fetch(url, target, expected_size):
    for attempt in range(3):
        try:
            with urlopen(url, timeout=60) as response, target.open('wb') as output:
                if urlparse(response.url).scheme != 'https':
                    raise ValueError('Non-HTTPS redirect')
                count = 0
                while block := response.read(1024 * 1024):
                    count += len(block)
                    if count > expected_size:
                        raise ValueError('Download exceeds manifest size')
                    output.write(block)
            return
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def run(manifest_path, destination, archive_dir=None):
    manifest = json.loads(manifest_path.read_text())
    bundles = manifest['archives']
    if archive_dir is None:
        for bundle in bundles:
            url = bundle.get('url')
            expected_path = f"/{manifest['repository']}/releases/download/{manifest['artifact_version']}/{bundle['name']}"
            if not url or urlparse(url)._replace(fragment='').geturl() != url:
                raise ValueError('Release URLs are unpublished; publication and pinned URLs are required')
            parsed = urlparse(url)
            if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.path != expected_path or parsed.query:
                raise ValueError('Expected exact versioned GitHub Release asset URL')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('Destination must be empty')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nazar-artifacts-') as scratch:
        scratch = Path(scratch)
        verified = scratch / 'verified'
        verified.mkdir()
        for bundle in bundles:
            archive = archive_dir / bundle['name'] if archive_dir else scratch / bundle['name']
            if archive_dir is None:
                fetch(bundle['url'], archive, bundle['size_bytes'])
            restore(archive, bundle, verified)
        for path in verified.iterdir():
            shutil.move(str(path), destination / path.name)
    print(f"Verified and restored {manifest['artifact_version']}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('manifest.json'))
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--archive-dir', type=Path, help='Offline verification of prepared archives')
    args = parser.parse_args()
    run(args.manifest, args.destination, args.archive_dir)
