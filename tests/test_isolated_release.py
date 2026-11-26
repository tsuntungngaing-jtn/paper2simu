import json
import zipfile
from pathlib import Path

import pytest

from scripts.check_isolated_release import REQUIRED, check_junit, check_zip, digest


def test_junit_counts_real_execution(tmp_path):
    path = tmp_path / 'results.xml'
    path.write_text('<testsuites><testsuite tests="2" failures="0" errors="0" skipped="1"><testcase/><testcase><skipped/></testcase></testsuite></testsuites>')
    assert check_junit(path)['executed'] == 1


@pytest.mark.parametrize('body', ['', '<testcase><skipped/></testcase>', '<testcase><failure/></testcase>', '<testcase><error/></testcase>'])
def test_junit_rejects_empty_skipped_or_failed(tmp_path, body):
    path = tmp_path / 'results.xml'
    path.write_text('<testsuite>' + body + '</testsuite>')
    with pytest.raises(ValueError):
        check_junit(path)


def test_zip_rejects_missing_required_source(tmp_path):
    path = tmp_path / 'release.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('paper2simu/RELEASE_MANIFEST.json', json.dumps({'files': []}))
    with pytest.raises(ValueError):
        check_zip(path, Path(__file__).resolve().parents[1])


def test_required_module_cannot_be_all_skipped(tmp_path):
    path = tmp_path / 'results.xml'
    path.write_text('<testsuite><testcase classname="test_other"/><testcase classname="test_isolated"><skipped/></testcase></testsuite>')
    with pytest.raises(ValueError, match='did not execute'):
        check_junit(path, ['test_isolated'])


def test_complete_zip_and_hashes(tmp_path):
    root = tmp_path / 'source'
    files = {}
    for name in REQUIRED:
        source = root / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('fixture', encoding='utf-8')
        files[name] = source.read_bytes()
    path = tmp_path / 'release.zip'
    manifest = {'files': [dict(path=n, bytes=len(b), sha256=digest(b)) for n, b in files.items()]}
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in files.items():
            archive.writestr('paper2simu/' + name, data)
        archive.writestr('paper2simu/RELEASE_MANIFEST.json', json.dumps(manifest))
    checksum = path.with_suffix('.zip.sha256')
    checksum.write_text(digest(path.read_bytes()) + '  release.zip\n')
    assert check_zip(path, root)['required_sources'] == len(REQUIRED)
    checksum.write_text('0' * 64)
    with pytest.raises(ValueError, match='checksum'):
        check_zip(path, root)
