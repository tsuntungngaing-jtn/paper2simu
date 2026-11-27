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
