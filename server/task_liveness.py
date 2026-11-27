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
        key = [plan["task_id"], resource, node, incident]
        ident = "recover-" + hashlib.sha256(json.dumps(key,separators=(",",":")).encode()).hexdigest()[:32]
        # Preserve existing candidate identities from the earlier key scheme.
        # An incident is an externally reviewed stable ID, not a text label.
        legacy_types = ("input_missing","physics_unresolved","model_incomplete",
                        "capability_missing","deployment_mismatch","transport_error",
                        "native_solver_failure","comparison_ambiguous")
        legacy_ids = {"recover-" + hashlib.sha256(json.dumps(
            [plan["task_id"],resource,node,kind,incident],separators=(",",":")
        ).encode()).hexdigest()[:32] for kind in legacy_types}
        if ident in nodes or legacy_ids.intersection(nodes) or any(
                n.get("blocked_node") == node and n.get("incident_id") == incident
                and n.get("resource_domain") == resource for n in nodes.values()):
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


def observation_replay(records, threshold=2):
    """Production replay contract: distinct original turns, stable facts only.

    Host maps source events to these fields using reviewed mappings. No prose
    comparison or inferred progress; an event with unknown mapping stays a gap.
    One final observation per source turn, in original journal order.
    """
    states = {"PENDING","READY","AUTHORIZED","DISPATCHED","RUNNING",
              "BLOCKED","COMPLETED","VERIFIED","FAILED","UNKNOWN"}
    codes = {"input_missing","physics_unresolved","model_incomplete",
             "capability_missing","deployment_mismatch","transport_error",
             "native_solver_failure","comparison_ambiguous"}
    seen, ordered = {}, []
    for row in records:
        source = row.get("source_turn_id")
        if not isinstance(source,str) or not source.strip():
            raise ValueError("missing original turn ID")
        node_states = row.get("node_states")
        if not isinstance(node_states,dict) or any(
                not isinstance(k,str) or v not in states for k,v in node_states.items()):
            raise ValueError("unknown node state")
        blockers = []
        for item in row.get("blockers",[]):
            if not all(isinstance(item.get(k),str) and item[k] for k in
                       ("incident_id","resource_domain","node_id")) or item.get("code") not in codes:
                raise ValueError("unmapped blocker")
            blockers.append({k:item[k] for k in ("incident_id","resource_domain","node_id","code")})
        milestones = row.get("verified_milestones")
        ready = row.get("eligible_ready")
        if not isinstance(milestones,list) or not isinstance(ready,list) or not all(
                isinstance(x,str) and x for x in milestones+ready):
            raise ValueError("missing stable milestone or ready ID")
        facts = dict(node_states=node_states,blockers=sorted({
            json.dumps(x,sort_keys=True) for x in blockers}),
            verified_milestones=sorted(set(milestones)),eligible_ready=sorted(set(ready)))
        fingerprint = json.dumps(facts,sort_keys=True)
        if source in seen:
            if seen[source] != fingerprint:
                raise ValueError("conflicting observations for original turn")
            continue
        seen[source] = fingerprint
        ordered.append(facts)
    return {"status":repeated_observations(ordered,threshold),
            "input_count":len(records),"unique_turns":len(ordered),
            "native_execution_authorized":False}


def verify_completion_receipt(plan, event, root, approved_index):
    """Check an independently approved retained review projection.

    The caller must independently establish the index's authority and actual
    worker identities. A hash alone is not authentication or a scientific PASS.
    """
    from server.receipt_evidence import load_receipt
    node = next((n for n in plan["work_nodes"] if n["id"] == event["node_id"]),None)
    if node is None or event.get("revision_binding") != node["revision_binding"]:
        raise ValueError("unknown node or stale revision")
    receipt = load_receipt(root,approved_index,event.get("review_receipt"))
    expected = {"task_id":plan["task_id"],"node_id":node["id"],
                "revision_binding":node["revision_binding"],
                "evidence_refs":sorted(set(event["evidence_refs"])),
                "decision":"ACCEPT_COMPLETION"}
    if any(receipt.get(k) != v for k,v in expected.items()):
        raise ValueError("review receipt scope or evidence mismatch")
    if receipt.get("producer_role") != node["owner_role"] or receipt.get("reviewer_role") not in {"A03","A05","A07"}:
        raise ValueError("invalid review role")
    producer, reviewer = receipt.get("producer_worker"),receipt.get("reviewer_worker")
    if not all(isinstance(v,str) and v.strip() for v in (producer,reviewer)) or producer == reviewer:
        raise ValueError("independent worker identities required")
    return True
