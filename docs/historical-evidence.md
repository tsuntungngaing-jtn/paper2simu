# Historical evidence protocol v1

The local verifier accepts a narrowly scoped conclusion about a process that ran entirely on this host before a later Windows boot. A successful verification authorizes consideration of one historical admission blocker. Live leases, current jobs, scientific acceptance and Case Clock records have their own authorities.

## Trust and custody

Provision a deployment-controlled JSON trust file outside all agent, report and output write locations. Its fields are `host_id` (the case-folded local hostname), `resource_id`, and `principals`. The latter maps individual principal IDs to objects with `role` and `public_key` (standard base64 raw Ed25519 public key). Use separate custodians and keys for `independent_reviewer` and `resource_admin`. Restrict trust-file and ledger writes using operating-system permissions. Keep reviewed artifacts available read-only at their canonical absolute paths. Archive trust revisions before rotating keys.

The independent reviewer must establish provenance and local-only execution from original connection, deployment and job records, including absence of remote workers. The resource administrator must independently verify domain ownership and the scope of release. XML exports and normalized origin records are portable files. Their hashes establish byte identity. Their authenticity and the completeness of execution-site evidence require the custodians' examination of the original sources. Unknown host continuity, reused hostnames, unverified boot evidence, unresolved remote workers, or missing provenance preclude signing.

## Signed packet

The packet contains exactly `statement`, `review` and `approval`. The statement binds the following fields.

- `job_id`, `operation_id` (JSON null when unavailable), `manifest_path`, and `manifest_sha256` identify the original job and exact manifest bytes. The filename stem is the original job ID.
- `host_id`, `resource_id`, and `event_at` identify the host, coordination domain and boot time (Unix seconds UTC).
- `historical_status` reproduces the manifest status. Supported conclusion fields are `process_lifecycle=LOCAL_PROCESS_ENDED_BY_BOOT_BOUNDARY`, `native_result=LOST_UNVERIFIED`, `resource_scope=CLEAR_THIS_HISTORICAL_BLOCK_ONLY`, `scientific_status=UNVERIFIED`, and `historical_budget=UNCHANGED`.
- `evidence` contains `origin` and `boot`, each with canonical absolute `path` and lowercase hex `sha256`. The origin JSON binds `job_id`, `operation_id`, `model_name`, `study_name`, `host_id`, `resource_id`, `submitted_at` `execution_site=LOCAL_ONLY`, and a nonempty `source_artifacts` array of canonical path/SHA-256 references to the original records supporting the local-only finding. Each source is reread and hashed. Export the original Windows System event as a single XML Event with provider Microsoft-Windows-Kernel-General, EventID 12, Computer and timezone-qualified TimeCreated. Its time must strictly follow submission.

Both signature records contain exactly `principal`, `signed_at` (Unix seconds UTC), and `signature` (standard base64 Ed25519 signature). The signed message is UTF-8 JSON using Python json.dumps with sort_keys=True, separators=(",", ":"), ensure_ascii=False and allow_nan=False. The reviewer signs an object containing protocol="paper2simu-reconciliation-v1", role="independent_reviewer", statement, principal and signed_at. The administrator signs the analogous message with role="resource_admin" plus the complete review record under review. Preserve numeric representations during signing and transport. Both signatures follow the boot event, and approval follows or coincides with review. Verification reopens the referenced evidence and never issues an approval.

The boot must strictly follow submission, all recorded original worker events, and known execution, start and completion timestamps. Runtime worker events are persisted by the original job's progress callback. An ambiguous or malformed worker event fails verification. A later journal recovery or client poll is an observation and its timestamp alone does not establish fresh execution. Windows SystemTime supports seven fractional digits.
