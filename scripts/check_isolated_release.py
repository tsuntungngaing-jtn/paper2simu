"""Validate actual offline test execution and complete, hash-bound release sources."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    'server/isolated_runtime.py', 'server/shared_guard.py',
    'tests/test_coordination.py', 'tests/test_isolated_executor.py',
    'tests/test_isolated_integration.py', 'tests/test_isolated_release.py',
    'scripts/check_multi_agent_v051.py', 'scripts/verification_gate.py',
    'scripts/recovery_memory.py', 'scripts/check_isolated_release.py',
    'references/recovery-history.json', 'benchmarks/runtime-capability-contract.json',
    'server/historical_evidence.py', 'server/historical_ledger.py',
    'tests/test_historical_evidence.py', 'tests/test_historical_ledger.py',
    'docs/historical-ledger.md', 'docs/historical-evidence.md', 'tests/test_historical_recovery.py', 'paper2simu/SKILL.md', 'pyproject.toml',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_junit(path, required_modules=()):
    path = Path(path)
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    skipped = sum(c.find('skipped') is not None for c in cases)
    failures = sum(c.find('failure') is not None for c in cases)
    errors = sum(c.find('error') is not None for c in cases)
    declared_bad = any(int(s.get('failures', '0')) or int(s.get('errors', '0')) for s in root.iter('testsuite'))
    executed = len(cases) - skipped
    if executed <= 0 or failures or errors or declared_bad:
        raise ValueError(f'Invalid test evidence: executed={executed}, failures={failures}, errors={errors}')
    for module in required_modules:
        if not any(module in c.get('classname', '').split('.') and c.find('skipped') is None for c in cases):
            raise ValueError('Required test module did not execute: ' + module)
    return dict(file=path.name, collected=len(cases), executed=executed,
                skipped=skipped, failures=failures, errors=errors,
                sha256=digest(path.read_bytes()))


def check_zip(path, root=ROOT):
    path, root = Path(path), Path(root)
    required = REQUIRED | {p.relative_to(root).as_posix() for folder in ('server', 'tests')
                           for p in (root / folder).rglob('*.py') if '__pycache__' not in p.parts}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive members')
        prefix = 'paper2simu/'
        present = {n.removeprefix(prefix) for n in names if n.startswith(prefix)}
        if required - present:
            raise ValueError('Missing release sources: ' + ', '.join(sorted(required - present)))
        manifest = json.loads(archive.read(prefix + 'RELEASE_MANIFEST.json'))
        records = manifest['files']
        indexed = {r['path']: r for r in records}
        if len(indexed) != len(records) or set(indexed) != present - {'RELEASE_MANIFEST.json'}:
            raise ValueError('Manifest membership mismatch')
        for name, record in indexed.items():
            data = archive.read(prefix + name)
            if len(data) != record['bytes'] or digest(data) != record['sha256']:
                raise ValueError('Manifest hash mismatch: ' + name)
        for name in required:
            if archive.read(prefix + name) != (root / name).read_bytes():
                raise ValueError('Stale packaged source: ' + name)
    checksum = path.with_suffix(path.suffix + '.sha256')
    if checksum.read_text(encoding='ascii').split()[0] != digest(path.read_bytes()):
        raise ValueError('ZIP checksum mismatch')
    return dict(file=path.name, files=len(names), bytes=path.stat().st_size,
                sha256=digest(path.read_bytes()), required_sources=len(required))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--junit', type=Path, action='append', default=[])
    parser.add_argument('--zip', type=Path)
    parser.add_argument('--require-test-module', action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.junit or args.zip is None:
        parser.error('Provide JUnit evidence and a release ZIP')
    report = dict(tests=[check_junit(p, args.require_test_module) for p in args.junit], release=check_zip(args.zip))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
