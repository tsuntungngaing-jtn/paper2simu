"""Runtime protection and MCP protocol tests; no COMSOL license/JVM required."""
import asyncio
import json
from pathlib import Path
import sys
import threading
import time
import socket
import subprocess
from types import SimpleNamespace

import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch

from server.main import BearerAuth, validate_token
from server.runtime import ROOT, Runtime, SerializedRegistrar, inside


TOKEN = "test-4LveZoVkRM79YS8dKaPWmDuT02QCAB"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)

    def test_token_required_and_paths_confined(self):
        tmp_path = self.tmp_path
        for value in (None, "", "short", "a" * 40):
            with self.assertRaises(ValueError):
                validate_token(value)
        assert validate_token(TOKEN) == TOKEN
        assert inside(tmp_path, "result/output.mph") == tmp_path / "result" / "output.mph"
        with self.assertRaises(ValueError):
            inside(tmp_path, "../escape.mph")
        with self.assertRaises(ValueError):
            inside(tmp_path, tmp_path.parent / "outside.mph")


    def test_auth_covers_sse_post_and_streamable_http(self):
        async def run():
            calls = []
            async def app(scope, receive, send):
                calls.append(scope["path"])
                await send({"type": "http.response.start", "status": 204, "headers": []})
                await send({"type": "http.response.body", "body": b""})
            auth = BearerAuth(app, TOKEN)
            for endpoint in ("/sse", "/messages/", "/mcp"):
                for header, status in ((None, 401), ("Bearer wrong", 401), ("Bearer " + TOKEN, 204)):
                    output = []
                    headers = [] if header is None else [(b"authorization", header.encode())]
                    async def send(message):
                        output.append(message)
                    await auth({"type": "http", "path": endpoint, "headers": headers,
                                "query_string": ("token=" + TOKEN).encode()}, None, send)
                    assert output[0]["status"] == status
            assert calls == ["/sse", "/messages/", "/mcp"]
        asyncio.run(run())


    def test_all_java_work_uses_one_thread_and_keeps_order(self):
        tmp_path = self.tmp_path
        runtime = Runtime(output_root=tmp_path)
        observed = []
        async def run():
            def work(number):
                observed.append((number, threading.get_ident()))
                return number
            assert await asyncio.gather(*(runtime.call(work, i) for i in range(8))) == list(range(8))
        try:
            asyncio.run(run())
            assert [item[0] for item in observed] == list(range(8))
            assert len({item[1] for item in observed}) == 1
            assert observed[0][1] != threading.get_ident()
        finally:
            runtime.executor.shutdown()


    def test_start_idempotent_disconnect_never_clears_models(self):
        tmp_path = self.tmp_path
        class FakeClient:
            version = "6.2"
            cores = 2
            standalone = False
            host = "localhost"
            port = 12345
            disconnected = False
            java = SimpleNamespace(tags=lambda: [])
            def clear(self):
                raise AssertionError("MUST NEVER CLEAR USER MODELS")
            def disconnect(self):
                self.disconnected = True
        client = FakeClient()
        class Manager:
            _client = None
            _models = {"existing": object()}
            current_model = "existing"
            @property
            def is_connected(self): return self._client is not None
            @property
            def client(self): return self._client
            @property
            def models(self): return self._models.copy()
        runtime = Runtime(output_root=tmp_path)
        manager = Manager()
        manager._client = client
        runtime.bind_manager(manager)
        runtime.client_handle = client
        assert runtime.start()["success"]
        assert "existing" in manager.models
        assert runtime.disconnect()["success"]
        assert client.disconnected
        assert "existing" in manager.models
        assert runtime.disconnect()["success"]
        runtime.executor.shutdown()


    def test_code_execution_disabled_without_explicit_opt_in(self):
        tmp_path = self.tmp_path
        env = patch.dict(os.environ, {"COMSOL_ALLOW_CODE": "0"})
        env.start()
        self.addCleanup(env.stop)
        runtime = Runtime(output_root=tmp_path)
        result = runtime.execute_code("missing", "raise RuntimeError('must not run')")
        assert not result["success"]
        assert "Disabled" in result["error"]
        runtime.executor.shutdown()


    def test_case_job_reports_build_failure_without_false_success(self):
        tmp_path = self.tmp_path
        examples = tmp_path / "examples"
        (examples / "original").mkdir(parents=True)
        (examples / "catalog.json").write_text(json.dumps({"cases": [{"id": "broken_example"}]}))
        (examples / "original" / "broken_example.py").write_text(
            "def build(client, outdir, progress, *, solve, study_name):\n"
            "    assert solve is False and study_name is None\n"
            "    progress('geometry')\n    raise RuntimeError('license unavailable')\n")
        runtime = Runtime(root=tmp_path, output_root=tmp_path / "runs")
        runtime.manager = SimpleNamespace(client=object())
        runtime.start = lambda: {"success": True}
        submitted = runtime.submit_case("broken_example", show_desktop=False)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = runtime.job_status(submitted["job_id"])
            if result["status"] == "failed":
                break
            time.sleep(0.01)
        assert result["status"] == "failed"
        assert "license unavailable" in result["error"]["message"]
        assert any(event["message"] == "geometry" for event in result["events"])
        assert (Path(result["output_dir"]) / "job-error.json").is_file()
        assert not runtime.submit_case("../private")["success"]
        runtime.executor.shutdown()

    def test_original_case_build_only_and_individual_study_routes(self):
        from examples.original.heat_sink_3d import build
        java_types = patch.multiple("examples.original.heat_sink_3d.jpype", JInt=int, JArray=lambda _: list)
        java_types.start()
        self.addCleanup(java_types.stop)
        for study_name in (None, "std1", "Transient"):
            with self.subTest(study_name=study_name):
                client = MagicMock()
                model = client.create.return_value
                java = model.java
                component = java.component().create.return_value
                component.selection().create.return_value.entities.return_value = [1]
                mesh = component.mesh().create.return_value
                mesh.stat().getNumElem.return_value = 1
                stationary, transient = MagicMock(), MagicMock()
                stationary.label.return_value = "Stationary"
                transient.label.return_value = "Transient"
                java.study().create.side_effect = [stationary, transient]
                stationary.run.side_effect = RuntimeError("Entered stationary solver")
                transient.createAutoSequences.side_effect = RuntimeError("Entered transient setup")
                if study_name is None:
                    result = build(client, self.tmp_path, lambda _: None)
                    self.assertFalse(result["solved_this_run"])
                    self.assertEqual(result["validation"], "not_run")
                    self.assertEqual(result["studies"], ["Stationary", "Transient"])
                    mesh.run.assert_called_once()
                    stationary.run.assert_not_called()
                    transient.createAutoSequences.assert_not_called()
                    java.sol.assert_not_called()
                elif study_name == "std1":
                    with self.assertRaisesRegex(RuntimeError, "Entered stationary solver"):
                        build(client, self.tmp_path, lambda _: None, solve=True, study_name=study_name)
                    transient.createAutoSequences.assert_not_called()
                else:
                    with self.assertRaisesRegex(RuntimeError, "Entered transient setup"):
                        build(client, self.tmp_path, lambda _: None, solve=True, study_name=study_name)
                    stationary.run.assert_not_called()

    def test_lost_submission_receipt_resolves_through_operation_id_after_restart(self):
        def solve(_):
            raise RuntimeError("Native failure fixture")

        model = SimpleNamespace(solve=solve)
        first = Runtime(output_root=self.tmp_path)
        first.manager = SimpleNamespace(is_connected=True, current_model="example", get_model=lambda _: model)
        try:
            submitted = first.submit_study("study", "example", operation_id="same-op")
            repeated = first.submit_study("study", "example", operation_id="same-op")
            self.assertEqual(submitted["job_id"], repeated["job_id"])
            self.assertTrue(repeated["existing_job"])
            self.assertEqual(first.submit_study("different", "example", operation_id="same-op")["error"],
                             "OPERATION_ID_CONFLICT")
        finally:
            first.executor.shutdown()
        restarted = Runtime(output_root=self.tmp_path)
        try:
            result = restarted.job_status(operation_id="same-op")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["job_id"], submitted["job_id"])
            self.assertTrue(result["historical"])
            self.assertEqual(result["runtime_id"], first.runtime_id)
            self.assertEqual(restarted.queue_status()["recovery_pending"], [])
            self.assertEqual(restarted.job_status(operation_id="absent")["status"], "unknown")
            self.assertTrue(restarted.submit_study("study", "example", operation_id="same-op")["existing_job"])
            self.assertEqual(restarted.queue_status()["submission_budget"]["submissions"]["used"], 1)
        finally:
            restarted.executor.shutdown()

    def test_busy_and_dead_are_distinguished_without_calling_stale_model(self):
        java = MagicMock()
        client = SimpleNamespace(java=java, host="localhost", port=12345, version="6.4", cores=2,
                                 standalone=False)

        def connect(port, host):
            client.port, client.host = port, host

        client.connect = connect
        type_manager = type("Manager", (), {
            "is_connected": property(lambda obj: obj._client is not None),
            "client": property(lambda obj: obj._client),
            "current_model": property(lambda obj: obj._current_model),
            "models": property(lambda obj: obj._models.copy()),
        })
        manager = type_manager()
        manager._client = client
        manager._current_model = "example"
        stale_model = MagicMock()
        manager._models = {"example": stale_model}
        runtime = Runtime(output_root=self.tmp_path)
        runtime.bind_manager(manager)
        runtime.client_handle = client
        runtime.last_endpoint = ("localhost", 12345)
        runtime.tracked_tags = {"example": "tag"}
        try:
            java.tags.side_effect = RuntimeError("Server is busy")
            self.assertEqual(runtime.status()["connection_state"], "busy")
            self.assertIs(manager._client, client)
            java.tags.side_effect = ConnectionResetError("Transport lost")
            self.assertEqual(runtime.status()["connection_state"], "dead")
            self.assertIsNone(manager._client)
            self.assertIsNone(client.port)
            self.assertEqual(manager._models, {})
            self.assertEqual(runtime.tracked_tags, {"example": "tag"})
            self.assertFalse(runtime.start()["success"])
            java.tags.side_effect = None
            java.tags.return_value = ["tag", "other-owner"]
            fresh = object()
            with patch("mph.Model", return_value=fresh) as wrap:
                self.assertTrue(runtime.connect(12345)["success"])
                wrap.assert_called_once_with(java.model.return_value)
            self.assertEqual(manager._models, {"example": fresh})
            stale_model.java.tag.assert_not_called()
        finally:
            runtime.executor.shutdown()

    def test_ambiguous_historical_operation_cannot_launch_replacement(self):
        manifests = self.tmp_path / 'job-manifests'
        manifests.mkdir()
        for job_id in ('first', 'second'):
            (manifests / f'{job_id}.json').write_text(json.dumps({
                'job_id': job_id, 'operation_id': 'conflict', 'status': 'completed',
            }), encoding='utf-8')
        runtime = Runtime(output_root=self.tmp_path)
        try:
            self.assertEqual(runtime.job_status(operation_id='conflict')['status'], 'unknown')
            self.assertEqual(runtime.job_status('first')['status'], 'completed')
            self.assertEqual(runtime.job_status('second')['status'], 'completed')
            self.assertEqual(runtime.submit_study(None, 'example', 'conflict')['error'], 'OPERATION_ID_AMBIGUOUS')
            self.assertFalse(runtime.futures)
        finally:
            runtime.executor.shutdown()

    def test_study_queue_cancel_and_nonblocking_status(self):
        runtime = Runtime(output_root=self.tmp_path)
        started = threading.Event()
        release = threading.Event()
        threads = []
        class Model:
            def solve(self, name):
                threads.append(threading.get_ident())
                started.set()
                release.wait(timeout=5)
            def name(self): return "example"
        runtime.manager = SimpleNamespace(is_connected=True, current_model="example", get_model=lambda name: Model())
        try:
            first = runtime.submit_study(None, "example")["job_id"]
            assert started.wait(timeout=2)
            assert runtime.job_status(first)["status"] == "running"
            assert not runtime.cancel_job(first)["success"]
            second = runtime.submit_study(None, "example")["job_id"]
            assert runtime.cancel_job(second)["status"] == "cancelled"
            release.set()
            done = asyncio.run(runtime.wait_job(first, timeout=2))
            assert done["status"] == "completed"
            assert threads and threads[0] != threading.get_ident()
            assert len(threads) == 1
        finally:
            release.set()
            runtime.executor.shutdown()

    def test_save_wrapper_preserves_public_model_name(self):
        runtime = Runtime(output_root=self.tmp_path)
        class Java:
            value = "Original.mph"
            def label(self, value=None):
                if value is not None: self.value = value
                return self.value
        model = SimpleNamespace(java=Java())
        model.name = lambda: Path(model.java.label()).stem
        runtime.manager = SimpleNamespace(get_model=lambda name: model)
        def model_save(model_name=None, file_path=None, format=None):
            model.java.label(Path(file_path).name)
            return {"success": True, "model": model.name()}
        wrapper = SerializedRegistrar(None, runtime)._wrap(model_save)
        try:
            result = asyncio.run(wrapper(file_path="changed.mph"))
            assert result["success"]
            assert result["model"] == "Original"
            assert model.java.label() == "Original.mph"
        finally:
            runtime.executor.shutdown()

    def test_case_catalog_compact_filter_and_details(self):
        (self.tmp_path / "examples").mkdir()
        cases = {"cases": [{"id": "sample", "category": "Heat", "title_zh": "Example", "learning_goals": ["long detail"]}]}
        (self.tmp_path / "examples" / "catalog.json").write_text(json.dumps(cases))
        runtime = Runtime(root=self.tmp_path, output_root=self.tmp_path / "runs")
        runtime.installation_root = lambda: self.tmp_path
        try:
            compact = runtime.list_cases(category="heat")
            assert compact["count"] == 1
            assert "learning_goals" not in compact["cases"][0]
            full = runtime.list_cases(case_id="sample", detail=True)
            assert full["cases"][0]["learning_goals"] == ["long detail"]
            assert not runtime.list_cases(case_id="missing")["success"]
        finally:
            runtime.executor.shutdown()


    def test_mcp_stdio_initialization_tools_and_status(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def run():
            params = StdioServerParameters(command=sys.executable, args=["-m", "server.main"], cwd=str(ROOT))
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    assert {"comsol_start", "model_create", "comsol_run_case", "comsol_job_status", "comsol_model_code"} <= names
                    discovered = {item.name:item for item in tools.tools}
                    for name in ('simulation_spec_validate','geometry_accept','selection_validate','selection_bind_checked','geometry_perturb','geometry_import_cad'):
                        assert name in discovered
                    assert 'properties' in discovered['geometry_add_feature'].inputSchema['properties']
                    invalid = await session.call_tool('simulation_spec_validate', {'document':{}})
                    assert json.loads(invalid.content[0].text)['status'] == 'FAIL'
                    missing = await session.call_tool('geometry_accept', {'requirements':[], 'model_name':'missing'})
                    assert json.loads(missing.content[0].text)['status'] == 'BLOCKED'
                    status = await session.call_tool("comsol_status", {})
                    assert not status.isError
                    payload = json.loads(status.content[0].text)
                    assert payload["connected"] is False
                    denied = await session.call_tool("comsol_model_code", {"model_name": "none", "code": "result=1"})
                    assert "Disabled" in denied.content[0].text
                    capabilities = await session.call_tool("comsol_execution_capabilities", {})
                    report = capabilities.structuredContent
                    self.assertEqual(report["paper2simu_version"], "0.5.2")
                    self.assertEqual(report["transport"], "stdio")
                    self.assertRegex(report["runtime_source_sha256"], "^[a-f0-9]{64}$")
                    self.assertEqual(report["capabilities"]["deadline_enforcement"]["state"], "unsupported")
                    for tool, payload in (("comsol_run_case", {"case_id": "heat_sink_3d"}),
                                          ("study_solve", {}), ("study_solve_async", {})):
                        outcome = await session.call_tool(tool, dict(payload, require_hard_deadline=True))
                        self.assertTrue(outcome.isError)
                        self.assertEqual(outcome.structuredContent["error"], "HARD_DEADLINE_UNSUPPORTED")
                    looked_up = await session.call_tool("comsol_job_status", {"operation_id": "test-missing"})
                    self.assertEqual(looked_up.structuredContent["status"], "unknown")
        asyncio.run(run())

    def test_stdio_budget_errors_and_local_renewal(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        (self.tmp_path / 'job-manifests').mkdir()
        (self.tmp_path / 'job-manifests/prior.json').write_text(
            json.dumps({'job_id': 'prior', 'status': 'running'}), encoding='utf-8')
        env = dict(os.environ, COMSOL_OUTPUT_ROOT=str(self.tmp_path), COMSOL_MAX_SUBMISSIONS='1',
                   COMSOL_SUBMISSION_WINDOW_SECONDS='86400', COMSOL_TOOL_ROLE='operator')

        async def run():
            params = StdioServerParameters(command=sys.executable, args=['-m', 'server.main'],
                                           cwd=str(ROOT), env=env)
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    status = await session.call_tool('comsol_queue_status', {})
                    self.assertFalse(status.isError)
                    self.assertEqual(status.structuredContent['recovery_pending'], ['prior'])
                    runtime_id = status.structuredContent['runtime_id']
                    receipt = subprocess.run(
                        [sys.executable, '-m', 'server.main', 'renew-window', '--runtime-id', runtime_id,
                         '--reason', 'Approved test renewal'],
                        env=env, cwd=ROOT, capture_output=True, check=True, timeout=10,
                    )
                    grant = Path(json.loads(receipt.stdout)['grant_path']).stem
                    for tool, arguments in (('study_solve', {}), ('study_solve_async', {}),
                                            ('comsol_run_case', {'case_id': 'heat_sink_3d'})):
                        with self.subTest(tool=tool):
                            result = await session.call_tool(tool, arguments)
                            self.assertTrue(result.isError)
                            self.assertEqual(result.structuredContent['reason'], 'TOTAL_SUBMISSION_LIMIT_REACHED')
                            budget = result.structuredContent['submission_budget']
                            self.assertEqual(budget['submissions']['used'], 1)
                            self.assertEqual(budget['window']['renewal_grant_id'], grant)
                            self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
        asyncio.run(run())

    def test_http_and_sse_real_protocol_with_bearer_auth(self):
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from mcp.client.sse import sse_client
        for transport, endpoint in (("streamable-http", "/mcp"), ("sse", "/sse")):
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                port = reservation.getsockname()[1]
            env = dict(os.environ, COMSOL_MCP_TOKEN=TOKEN, COMSOL_ALLOW_CODE="0")
            process = subprocess.Popen([sys.executable, "-m", "server.main", "--transport", transport, "--port", str(port)],
                                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            url = f"http://127.0.0.1:{port}{endpoint}"
            try:
                deadline = time.monotonic() + 20
                while True:
                    try:
                        response = httpx.get(url, timeout=0.5)
                        assert response.status_code == 401
                        break
                    except (httpx.ConnectError, httpx.ConnectTimeout):
                        if time.monotonic() > deadline or process.poll() is not None:
                            raise AssertionError(f"{transport} server did not start")
                        time.sleep(0.05)
                async def run():
                    factory = streamablehttp_client if transport == "streamable-http" else sse_client
                    async with factory(url, headers={"Authorization": "Bearer " + TOKEN}) as streams:
                        async with ClientSession(streams[0], streams[1]) as session:
                            await session.initialize()
                            tools = await session.list_tools()
                            assert "comsol_doctor" in {item.name for item in tools.tools}
                            status = await session.call_tool("comsol_status", {})
                            assert not status.isError
                            assert not json.loads(status.content[0].text)["connected"]
                asyncio.run(run())
            finally:
                process.terminate()
                process.wait(timeout=10)

if __name__ == "__main__":
    unittest.main()
