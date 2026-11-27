# Scheduled CLI host candidate (PC10 follow-up)

Stock Desktop has no verified accessible control endpoint on PC10. Do not
attach to a guessed pipe/socket or introduce a second concurrent writer.
This is an alternative host execution mode, not a Desktop reconnect patch.
It uses the installed official Codex CLI in noninteractive mode, a new local
process per scheduled turn, pinned task and Skill, and existing durable journals.
See https://developers.openai.com/codex/noninteractive and
https://developers.openai.com/codex/cli/reference.

## Migration (explicit opt-in, pilot only)

1. Keep production 0.6.2 unchanged until the pilot passes. Independently verify
   the old task's native state and outstanding operation IDs. Disable only the
   affected Desktop schedule after explicit approval; do not delete it. Ensure
   it cannot write in parallel. Never terminate COMSOL/Fluent to move hosts.
2. Provision an approved, separately configured CODEX_HOME and profile under
   the same authorized Windows account. Use the actual installed Codex executable,
   its existing approved auth mechanism, workspace and provider permissions.
   Do not export credentials or disable approvals/sandbox. For a read-only pilot
   use a genuinely provider-enforced read-only identity (shell sandbox is not
   MCP ACL). Check installed CLI help and actual provider startup; configure the
   required provider using its supported configuration if applicable. Do not
   assume COMSOL and Fluent share a connector or identity. Verify session-bound
   transport lifecycle and confirm that ending the CLI cannot terminate an
   active native job; otherwise this route is not admitted.
3. Keep the original task prompt, output roots, resume.md, journals, Case Clock,
   coordination and historical ledger. Configure one protected private state
   directory per resource domain across all cooperating scheduler instances.
   Protect it and the configuration/receipt with the actual local ACL.
   Independently verify native writer exclusion; the CLI lock alone cannot
   prevent Desktop or unrelated clients from writing.
4. Supply a private configuration JSON with these fields:
   schema = paper2simu-scheduled-cli/1; codex_executable; workspace; codex_home;
   state_dir; task_prompt; resume_file; skill_entry; migration_receipt (absolute
   paths); task_prompt_sha256; skill_sha256; migration_receipt_sha256;
   profile (approved name); observation_timeout_seconds (30..14400);
   desktop_schedule_disabled, exclusive_writer_verified,
   provider_permissions_verified, migration_authorized (all true only after
   real operator approval and evidence). A receipt hash checks bytes, not
   authority. Pin complete checkout and dependency fingerprints separately.
5. Run from the candidate checkout using its actual Python interpreter:
       python -m server.scheduled_cli ABSOLUTE_CONFIG_JSON --check-config
   This validates config shape and hashes, not execution permissions.
   Then run one read-only pilot invocation:
       python -m server.scheduled_cli ABSOLUTE_CONFIG_JSON
   Verify actual provider discovery and read-only operation in this CLI turn,
   original job identity, actual distinct agent permissions and full trace.
   Do not promote until the production profile is independently verified.
6. An authorized operator can configure Windows Task Scheduler to invoke the
   exact interpreter, module and config from the candidate checkout, using the
   original cadence and account, with no overlapping instances. This is a
   separate opt-in migration, not automatic scheduler creation. Do not configure
   Task Scheduler to forcibly stop the task or solver after a timeout.
   Store JSONL and stderr privately; never upload raw logs or secrets.

## Behavior and limits

A completed CLI lifecycle releases only the local scheduler-turn reservation.
The next scheduled invocation starts a fresh CLI process and reads original
resume.md, rediscovering MCP. It does not reuse Desktop's cached catalog.
It does not clear a solver claim, certify execution or reset a case clock.
An abnormal exit, timeout, crash, missing completion or invalid event stream
retains the local reservation. No automatic process kill or duplicate launch.
Inspect actual native history and the owned process, then use a separately
reviewed operator recovery/migration procedure; never delete the database or
reset a reservation to force progress. A clean CLI exit may still report HOLD.
If MCP startup is persistently broken, the fresh process does not repair it.
The CLI host is NOT_RUN with actual Codex, commercial solvers, actual Agent ACL,
cross-night scheduling and active native jobs. Fake subprocess tests only cover
local control flow. Do not claim PC10 recovery or move production from this
candidate until real native and scheduling acceptance is recorded.

Desktop reload remains optional and must block combined independent faults.
If a catalog failure leaves independent gates unknown, the reload path must
remain blocked; the missing-catalog symptom never overrides those gates.
