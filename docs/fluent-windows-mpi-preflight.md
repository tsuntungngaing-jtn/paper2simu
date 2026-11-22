# Fluent Windows MPI startup preflight

Use for an authorized Windows Fluent startup diagnostic when the current launch log shows license checkout followed by a hang or timeout at compute node 0 or another compute node. The examples match Fluent 2024 R2 (24.2). Verify the installed Fluent executable, Windows edition, PyFluent-MCP and PyFluent versions, and actual launch identity before applying them.

## Locate the failing stage

1. Read the current launch's transcript or console, license log and MCP session log together. Record MCP tool access, actual checkout, compute-node startup and Fluent gRPC readiness as independent observations. Follow the [licensing preflight](fluent-licensing-preflight.md) if this launch shows a denied checkout or dynamic port file write failure. If the native solver is ready and gRPC alone fails, check the provider's connection endpoint and server-info file through the [official MCP workflow](https://fluent-mcp.docs.pyansys.com/version/stable/getting_started/quick_start.html#connect-to-fluent).
2. In the local task record, capture the redacted effective launch settings, actual MPI and node count when reported, host-file and scheduler options, Windows edition and logical processor count, working directory, process owner and last native progress line. Compare local and explicit-host launch settings to narrow the failing path. Match the Fluent transcript before attributing a failure to Microsoft MPI, DNS, an adapter, credentials, or firewall policy.
3. Check the original job and process ownership before any new launch. Start a single isolated empty session at a time under the intended launch identity. Use a writable local diagnostic directory. Keep the case, mesh, journal and production schedule out of this check. If a client call times out, recheck session status and the owned processes before retrying. Close the diagnostic session through its supported lifecycle and verify its Fluent/MPI children have exited before starting the next trial.

## Run a local startup comparison

Use the registered official Fluent solve provider and inspect the installed tool schema. The current upstream Solve `connect` accepts `backend_kind` and `connect_kwargs`. The minimal 24.2 launch example below applies to that schema. Adjust dimension and precision to match the intended workload and keep them fixed within the comparison. Leave out attach credentials, host files, scheduler options, startup case/data/journal and GPU options. Verify that inherited launcher settings and the effective command also use the local machine without a host file.

```json
{
  "backend_kind": "pyfluent",
  "connect_kwargs": {
    "product_version": "24.2.0",
    "mode": "solver",
    "dimension": 3,
    "precision": "double",
    "processor_count": 1
  }
}
```

| Trial | Change | Evidence to record |
| --- | --- | --- |
| A. One-process baseline | Start with `processor_count: 1`. If the original launch's MPI is known and supported and the provider can pass it through, preserve that MPI during A and B. | Native startup and successful read-only access through the registered provider. One process is a baseline and may still use the build's startup infrastructure. |
| B. Two processes on the local machine | After A is verified and closed, use `processor_count: 2` with the same effective MPI and other options. Set the original supported MPI explicitly if otherwise ambiguous. | If it works, compare the original command for an explicit host file, distributed mode or scheduler setting. Leave those out of a confirmed single-workstation recipe. |
| C. Compare MPI implementations if B fails | On a supported Windows desktop installation with both MPI implementations available, hold B's settings fixed. Change only `additional_arguments` from `-mpi=msmpi` to `-mpi=intel`, or the reverse if B used Intel. Verify the effective MPI in the native transcript. | A successful alternate launch identifies a workable local configuration for this test. Keep the exact cause of the original failure open. |

Fluent 2024 R2 uses Intel MPI as the usual Windows default and switches the default to Microsoft MPI on systems with more than 64 logical cores. On Windows Server, this release supports only Microsoft MPI for parallel Fluent. Skip the Intel trial there. Treat failures from an unsupported OS, license tier or provider/build combination as compatibility findings. PyFluent documents Fluent Pro as unsupported.

If A fails, preserve the startup log and process state. Use the operator's Ansys Fluent Launcher for an isolated check of the same build and identity if available and authorized. If the installed MCP cannot forward the needed launch options, the operator can use 2024 R2 Fluent Launcher's **Parallel Settings** to select the supported MPI, or use the version-matched native command, for example `fluent 3ddp -t2 -mpi=msmpi` from the configured Fluent command environment. Use the local-machine settings and an empty session. Any later connection to an existing session must use the registered provider's explicit attach mode and a verified gRPC endpoint. Keep credentials and server-info files local.

If local launches still hang, use the actual failing command and logs to check local hostname resolution and chosen interface, MPI launcher prompts or service events, and firewall deny records. For a solver that is already ready, investigate the gRPC path separately. Change Windows networking, security rules, licensing or MPI service settings only for an evidenced cause within the operator's authorization. Increasing either the gRPC wait or the native compute-node timeout leaves a reproducible startup hang unresolved.

Record each trial's native start result, gRPC result, effective arguments, exit evidence and elapsed time. Keep the production solve budget and timer tied to the production task's own start condition. An empty startup test does not validate the production model, partitioning or solve.

## Official references

- [Fluent 2024 R2 Windows parallel startup and MPI flags](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_parallel_start_windows.html)
- [Fluent 2024 R2 startup options and timeout](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_ug_startramp.html)
- [Fluent 2024 R2 platform and MPI limits](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/flu_ug/flu_gs_limitations.html)
- [Official MCP `connect` schema](https://github.com/ansys/pyfluent-mcp/blob/8a712b3b091932f63105d9e54cc6a725f14e7100/src/ansys/fluent/mcp/common/base.py#L1045) and [PyFluent backend launch options](https://fluent-mcp.docs.pyansys.com/version/stable/api/ansys/fluent/mcp/solve/backends/pyfluent/PyFluentBackend.html)
- [PyFluent compatibility](https://fluent.docs.pyansys.com/version/stable/index.html#compatibility) and [PyFluent launch arguments](https://fluent.docs.pyansys.com/version/stable/api/execution/launcher/launcher.html)
