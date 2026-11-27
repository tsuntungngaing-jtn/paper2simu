"""Derive recovery candidates from existing plan/journal, no second state store.

No authorization or agent dispatch. The actual host must approve revisions,
enforce existing gates and append original events through its unique writer.
"""
import hashlib
import json
from graphlib import TopologicalSorter

ROLES = {"A%02d" % i for i in range(10)}
SCOPES = {"read_only", "host_refresh", "native_attach", "native_mutation",
          "native_submission", "independent_review"}


def validate_nodes(plan):
    """Opt-in strict revision; existing plans remain readable."""
    schema = plan.get("work_schema")
    if schema is None:
        return False
    if schema != "work-nodes/2":
        raise ValueError("unknown work schema")
    nodes = plan.get("work_nodes")
    if not isinstance(nodes,list) or not nodes:
        raise ValueError("strict unattended plan needs work_nodes")
    ids = {n["id"] for n in nodes}
    if len(ids) != len(nodes):
        raise ValueError("duplicate nodes")
    graph, failure = {}, {}
    for n in nodes:
        if n.get("owner_role") not in ROLES or n.get("operation_scope") not in SCOPES:
            raise ValueError("missing role or scope")
        for k in ("id", "action", "completion_evidence", "resource_domain", "revision_binding"):
            if not isinstance(n.get(k),str) or not n[k].strip():
                raise ValueError("missing " + k)
        for k in ("depends_on","failure_edges"):
            v = n.get(k)
            if not isinstance(v,list) or any(x not in ids for x in v):
                raise ValueError("invalid " + k)
        if type(n.get("attempt_budget")) is not int or n["attempt_budget"] < 0:
            raise ValueError("invalid attempt budget")
        if n["operation_scope"] == "native_submission" and n.get("requires_submission") is not True:
            raise ValueError("native submission must use existing budget gate")
        if n["operation_scope"] == "read_only" and (n.get("requires_submission") or n.get("requires_idle_solver")):
            raise ValueError("split read-only and native admission nodes")
        if n["operation_scope"] in ("native_attach","native_mutation","native_submission") and n["owner_role"] != "A04":
            raise ValueError("native execution requires existing Executor")
        graph[n["id"]] = n["depends_on"]
        failure[n["id"]] = n["failure_edges"]
    list(TopologicalSorter(graph).static_order())
    list(TopologicalSorter(failure).static_order())
    for source, targets in failure.items():
        for target in targets:
            pending, seen = list(graph[target]), set()
            while pending:
                item = pending.pop()
                if item == source:
                    raise ValueError("failure route waits on failed source")
                if item not in seen:
                    seen.add(item)
                    pending.extend(graph[item])
    return True


def recovery_candidates(plan, blockers):
    """Stable per existing incident; proposals do not add retry budget."""
    nodes = {n["id"]: n for n in plan.get("work_nodes", [])}
    result = []
    for node, event in sorted(blockers.items()):
        incident = event.get("incident_id")
        resource = nodes[node].get("resource_domain")
        if not isinstance(incident,str) or not incident or not isinstance(resource,str) or not resource:
            continue
        key = [plan["task_id"], resource, node, event["blocker_type"], incident]
        ident = "recover-" + hashlib.sha256(json.dumps(key,separators=(",",":")).encode()).hexdigest()[:32]
        if ident in nodes:
            continue
        result.append({"id":ident,"blocked_node":node,"owner_role":"A06",
                       "operation_scope":"read_only","incident_id":incident,
                       "depends_on":[],"resource_domain":resource,
                       "action":"Inspect existing evidence and propose a scoped recovery",
                       "proposed_next_action":event["next_action"],
                       "completion_evidence":event["resume_when"],
                       "status":"PROPOSED_VERIFY_AUTHORIZATION",
                       "native_execution_authorized":False})
    return result


def repeated_observations(observations, threshold=2):
    """Workflow triage from trusted normalized facts, not a native stall rule."""
    if type(threshold) is not int or threshold < 2:
        raise ValueError("invalid threshold")
    keys = ("node_states", "blockers", "verified_milestones", "eligible_ready")
    def fingerprint(item):
        if any(k not in item for k in keys):
            raise ValueError("incomplete observation")
        # These three fields are sets of normalized observations, not event order.
        def canonical(value):
            return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
        normalized = {"node_states":item["node_states"]}
        if not isinstance(normalized["node_states"],dict):
            raise ValueError("node_states must map stable node IDs to state")
        for key in ("blockers","verified_milestones","eligible_ready"):
            if not isinstance(item[key],list):
                raise ValueError(key + " must be a list")
            normalized[key] = sorted({canonical(v) for v in item[key]})
        return canonical(normalized)
    if len(observations) < threshold:
        return "INSUFFICIENT_OBSERVATIONS"
    tail = observations[-threshold:]
    if len({fingerprint(i) for i in tail}) != 1:
        return "STATE_CHANGED"
    return "REPLAN_READY_WORK" if tail[-1]["eligible_ready"] else "WAIT_OR_ESCALATE_MINIMAL_BLOCKER"


def migration_preview(plan, reviewed_nodes):
    """Return a proposed revision, never write or infer missing permissions.

    reviewed_nodes maps existing node IDs to explicit reviewed metadata.
    Preserve old IDs, actions, dependencies and native guards. New tasks need
    a separately approved plan revision; do not infer them from prose.
    """
    from copy import deepcopy
    proposed = deepcopy(plan)
    nodes = proposed.get("work_nodes", [])
    ids = {n["id"] for n in nodes}
    if set(reviewed_nodes) - ids:
        raise ValueError("unknown existing node in migration")
    fields = {"owner_role","operation_scope","completion_evidence",
              "resource_domain","revision_binding","attempt_budget","failure_edges"}
    for node in nodes:
        supplied = reviewed_nodes.get(node["id"], {})
        if set(supplied) - fields:
            raise ValueError("migration must preserve original node and gates")
        for key, value in supplied.items():
            if key in node and node[key] != value:
                raise ValueError("existing metadata conflicts: " + node["id"])
            node[key] = deepcopy(value)
        node.setdefault("depends_on", [])
    gaps = [{"node_id":n["id"],"missing":sorted(fields-set(n))}
            for n in nodes if fields-set(n)]
    if not nodes or gaps:
        return {"status":"MIGRATION_INCOMPLETE","gaps":gaps,
                "native_execution_authorized":False}
    proposed["work_schema"] = "work-nodes/2"
    validate_nodes(proposed)
    return {"status":"PROPOSED_REVIEW_REQUIRED","plan":proposed,
            "native_execution_authorized":False}


def reviewed_completion(plan, node_id, revision, evidence_refs, review_receipt):
    """Build an event proposal for the existing journal, not a completion claim.

    The authorized writer must validate actual evidence and independence,
    dependencies and blockers using the original renderer before appending.
    """
    nodes = {n["id"]:n for n in plan.get("work_nodes",[])}
    if node_id not in nodes or nodes[node_id].get("revision_binding") != revision:
        raise ValueError("unknown node or stale revision")
    if not isinstance(evidence_refs,list) or not evidence_refs or not all(
            isinstance(x,str) and x.strip() for x in evidence_refs):
        raise ValueError("missing completion evidence")
    if not isinstance(review_receipt,str) or not review_receipt.strip():
        raise ValueError("missing review receipt")
    return {"event":"work_completed","node_id":node_id,
            "revision_binding":revision,"evidence_refs":sorted(set(evidence_refs)),
            "review_receipt":review_receipt}
