"""Classify observed official-provider handshake stages without launching it."""
STAGES = [
        ("configured","NOT_CONFIGURED"),
        ("environment_ok","EXECUTABLE_ENV_INVALID"),
        ("child_started","CHILD_START_FAILED"),
        ("child_alive_at_initialize","CHILD_EXIT_BEFORE_INITIALIZE"),
        ("stdout_protocol_clean","STDOUT_PROTOCOL_CONTAMINATION"),
        ("initialize_response","INITIALIZE_FAILED_OR_TIMEOUT"),
        ("protocol_compatible","PROTOCOL_MISMATCH"),
        ("initialized","INITIALIZED_NOTIFICATION_FAILED"),
        ("tools_list_ok","TOOLS_LIST_FAILED"),
        ("host_catalog_ok","CATALOG_UNAVAILABLE"),
        ("native_attach_ok","NATIVE_ATTACH_FAILED"),
        ("license_ok","LICENSE_UNVERIFIED_OR_FAILED"),
    ]
def classify(observed):
    for key, failure in STAGES:
        value = observed.get(key)
        if value is None:
            return {"status":"UNKNOWN","next_evidence":key,"native_execution_authorized":False}
        if type(value) is not bool:
            raise ValueError("invalid tri-state evidence")
        if not value:
            return {"status":failure,"next_evidence":key,"native_execution_authorized":False}
    return {"status":"DECLARED_STAGES_OBSERVED","native_execution_authorized":False}


def classify_receipts(root, approved_index, receipt_ids, expected_context):
    """Replay redacted same-context observations; no claim of host authenticity."""
    from server.receipt_evidence import load_receipt
    keys = ("host_id","turn_id","provider_id")
    if "launch_id" in expected_context:
        keys += ("launch_id",)
    if "origin" in expected_context:
        keys += ("origin",)
    if not all(isinstance(expected_context.get(k),str) and expected_context[k] for k in keys):
        raise ValueError("missing context")
    observed = {}
    verified = set()
    for ident in receipt_ids:
        receipt = load_receipt(root, approved_index, ident)
        if any(receipt.get(k) != expected_context[k] for k in keys):
            raise ValueError("receipt from another context")
        stage, value = receipt.get("stage"), receipt.get("observed")
        allowed = {"configured","environment_ok","child_started","child_alive_at_initialize",
                   "stdout_protocol_clean","initialize_response","protocol_compatible",
                   "initialized","tools_list_ok","host_catalog_ok","native_attach_ok","license_ok"}
        if stage not in allowed or (value is not None and type(value) is not bool):
            raise ValueError("invalid stage receipt")
        if stage in observed and observed[stage] is not value:
            raise ValueError("conflicting stage evidence")
        observed[stage] = value
        verified.add(ident)
    out = classify(observed)
    out["receipt_bytes_verified"] = bool(verified)
    out["verified_receipt_count"] = len(verified)
    out["known_failed_stages"] = sorted(k for k,v in observed.items() if v is False)
    out["observed_stages"] = sorted(k for k,v in observed.items() if v is not None)
    out["first_unresolved_stage"] = out.get("next_evidence")
    out["first_missing_stage"] = next((k for k,_ in STAGES if observed.get(k) is None),None)
    out["first_failed_stage"] = next((k for k,_ in STAGES if observed.get(k) is False),None)
    out["authenticity_verified"] = False
    return out
