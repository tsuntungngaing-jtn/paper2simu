"""Classify observed official-provider handshake stages without launching it."""
def classify(observed):
    order = [
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
    for key, failure in order:
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
    if not all(isinstance(expected_context.get(k),str) and expected_context[k] for k in keys):
        raise ValueError("missing context")
    observed = {}
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
    out = classify(observed)
    out["receipt_bytes_verified"] = True
    out["authenticity_verified"] = False
    return out
