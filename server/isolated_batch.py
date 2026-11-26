"""Local v0.4.0 patch: MCP-owned isolated Windows batch deadline execution.

Public submit accepts only a saved MPH, a study tag and a frozen absolute
deadline; generic commands are private test/supervisor plumbing.
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

PATCH_VERSION = 'windows-isolated-deadline-2'
TERMINAL = {'process_completed', 'process_failed', 'deadline_terminated', 'expired_not_started', 'launch_failed'}


def read_json(path):
    for attempt in range(100):
        try:return json.loads(path.read_text(encoding='utf-8'))
        except PermissionError:
            if attempt==99:raise
            time.sleep(.005)


def isolated_pending(root):
    for folder in (Path(root)/'isolated-jobs').glob('*'):
        if not folder.is_dir():continue
        try:
            request=json.loads((folder/'request.json').read_text(encoding='utf-8'))
            if status(root,request['operation_id'])['status'] not in TERMINAL:return True
        except (OSError,ValueError,KeyError):
            return True
    return False


@contextmanager
def admission_lock(directory):
    import msvcrt
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/'.admission.lock').open('a+b') as handle:
        handle.seek(0); handle.write(b'0'); handle.flush(); handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            yield
        finally:
            handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def _folder(root, operation_id):
    if not isinstance(operation_id, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', operation_id):
        raise ValueError('Invalid operation_id')
    return Path(root).resolve()/'isolated-jobs'/hashlib.sha256(operation_id.encode()).hexdigest()[:32]


def status(root, operation_id):
    from .windows_job import process_identity
    folder = _folder(root, operation_id)
    if not (folder/'request.json').exists():
        return {'status': 'unknown_incomplete_manifest' if folder.exists() else 'unknown_operation', 'operation_id': operation_id}
    request = json.loads((folder/'request.json').read_text(encoding='utf-8'))
    path = folder/'state.json'
    state = read_json(path) if path.exists() else {
        'status': 'unknown_starting', 'operation_id': operation_id,
        'deadline_at_unix': request['deadline_at_unix']}
    if state['status'] not in TERMINAL and state.get('supervisor_pid'):
        identity = process_identity(state['supervisor_pid'])
        if identity is None or abs(identity-state['supervisor_created_at'])>.001:
            state['status'] = 'unknown_supervisor_lost'
    state['job_directory'] = str(folder)
    state['patch_version'] = PATCH_VERSION
    return state


def _launch(root, command, operation_id, deadline_at_unix, reserve_seconds=2.0, metadata=None):
    if os.name != 'nt':
        raise RuntimeError('isolated deadline requires Windows')
    if not isinstance(deadline_at_unix, (int,float)) or not math.isfinite(deadline_at_unix):
        raise ValueError('finite deadline required')
    folder = _folder(root, operation_id)
    stable = dict(command=command, operation_id=operation_id, deadline_at_unix=deadline_at_unix,
                  reserve_seconds=reserve_seconds, metadata=metadata or {})
    with admission_lock(folder.parent):
        if folder.exists():
            prior = json.loads((folder/'request.json').read_text(encoding='utf-8'))
            if any(prior.get(k)!=v for k,v in stable.items()):
                raise ValueError('operation_id conflicts with original request')
            return folder
        if deadline_at_unix-time.time()<=reserve_seconds:
            raise ValueError('deadline expired or insufficient remaining budget')
        for manifest in (Path(root)/'job-manifests').glob('*.json'):
            try:
                shared=json.loads(manifest.read_text(encoding='utf-8'))
            except (OSError,ValueError) as exc:
                raise RuntimeError('Unresolved shared manifest blocks admission') from exc
            if shared.get('status') not in {'completed','failed','cancelled'}:
                raise RuntimeError('An active or unresolved shared job blocks admission')
        if isolated_pending(root):
            raise RuntimeError('An active or unresolved isolated job blocks admission')
        folder.mkdir()
        stable['submitted_at_unix'] = time.time()
        from .isolated_worker import atomic_write
        from .windows_job import process_identity
        atomic_write(folder/'request.json',stable)
        try:
            with (folder/'supervisor.log').open('ab') as stream:
                process=subprocess.Popen([sys.executable,'-m','server.isolated_worker',str(folder)],
                             cwd=str(Path(__file__).resolve().parents[1]),
                             stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,
                             close_fds=True,creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as exc:
            atomic_write(folder/'state.json',dict(status='launch_failed',operation_id=operation_id,
                deadline_at_unix=deadline_at_unix,error=str(exc),native_status='NOT_RUN'))
            raise
        atomic_write(folder/'launch.json',dict(supervisor_pid=process.pid,
            supervisor_created_at=process_identity(process.pid),launched_at_unix=time.time()))
    return folder


def submit(root, input_file, study_tag, operation_id, deadline_at_unix, cores=4):
    root = Path(root).resolve()
    if deadline_at_unix-time.time()>14400:
        raise ValueError('deadline exceeds 14400 seconds maximum')
    input_path = Path(input_file).resolve()
    if not input_path.is_relative_to(root):
        raise ValueError('MPH must remain within output root')
    if input_path.suffix.lower()!='.mph' or not input_path.is_file():
        raise ValueError('Existing saved MPH required')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',study_tag):
        raise ValueError('Native study tag required')
    if type(cores) is not int or not 1<=cores<=4:
        raise ValueError('cores must be 1..4')
    exe = Path(os.environ.get('COMSOL_ROOT',r'D:\Program Files\COMSOL\COMSOL64\Multiphysics'))/'bin'/'win64'/'comsolbatch.exe'
    if not exe.is_file():
        raise ValueError('Configured COMSOL batch executable missing')
    folder = _folder(root,operation_id)
    # Replay uses original command, including its original native relative stoptime.
    if folder.exists():
        prior=json.loads((folder/'request.json').read_text(encoding='utf-8'))
        meta=prior.get('metadata',{})
        if (meta.get('input_file')!=str(input_path) or meta.get('study_tag')!=study_tag or
                prior['deadline_at_unix']!=deadline_at_unix or meta.get('cores')!=cores):
            raise ValueError('operation_id conflicts with original request')
        return status(root,operation_id)
    digest=hashlib.sha256(input_path.read_bytes()).hexdigest()
    command=[str(exe),'-np',str(cores),'-inputfile',str(input_path),'-outputfile',str(folder/'result.mph'),
             '-study',study_tag,'-batchlog',str(folder/'native.log'),'-alivetime','1',
             '-stoptime',str(max(1,int(deadline_at_unix-time.time()-10)))]
    _launch(root,command,operation_id,deadline_at_unix,metadata=dict(
        input_file=str(input_path),input_sha256=digest,study_tag=study_tag,cores=cores,
        enforcement='Windows Job Object; creation-time assignment; kill-on-close',
        native_status='NOT_RUN',source_version='0.4.0',patch_version=PATCH_VERSION))
    return status(root,operation_id)
