"""v0.6.4-dev composition layer. Local, opt-in, no native execution.

Uses existing journal, evidence and gates. Does not invent actual host APIs.
All external calls and approvals must be provided by a trusted host.
"""
from server.readonly_dispatch import append_event,project,snapshot,_file_identity,READ_ROLES
from server.revision_transactions import activate_revision,active_segment
from server.journal_anchor import require_anchor
from server.review_authority import require_authority,require_verified,content_digest
from server.host_observation import observe_dispatch
from server.journal_reconciliation import reconcile_owner
from pathlib import Path


class ResearchTransaction:
    def __init__(self,journal,store):
        self.journal=Path(journal).resolve(strict=True)
        self.store=store

    def anchor(self):
        anchor,pending=self.store.inspect()
        if pending is not None:
            raise ValueError("checkpoint transaction unresolved")
        return anchor

    def append(self,plan,event,**kwargs):
        anchor=self.anchor()
        return append_event(plan,self.journal,event,expected_sha256=anchor.journal_sha256,
                            journal_anchor=anchor,checkpoint_store=self.store,**kwargs)

    def activate(self,history,event,**kwargs):
        anchor=self.anchor()
        return activate_revision(history,self.journal,event,expected_sha256=anchor.journal_sha256,
                                 journal_anchor=anchor,checkpoint_store=self.store,**kwargs)

    def candidates(self,plan,*,root,index,authority,history=None):
        from scripts.research_resume import work_progress
        from server.readonly_dispatch import _read,verify_historical_dispatch,KINDS
        anchor=self.anchor()
        raw,events=_read(self.journal)
        require_authority(plan,index,authority)
        require_anchor(anchor,task_id=plan["task_id"],genesis_sha256=history.initial_plan_sha256 if history else content_digest(plan),
                       raw=raw,events=events,identity=_file_identity(self.journal.stat()),authority=authority)
        if history:
            h=active_segment(history,events,root,index,authority)
            if h["active_plan_sha256"]!=content_digest(plan):
                raise ValueError("inactive plan")
            segment,spent=h["events"],h["attempts"]
        else:
            if any(e.get("event")=="revision_activated" for e in events):
                raise ValueError("revision history required")
            segment=events
            spent={}
            for e in events:
                if e.get("event") in KINDS:
                    verify_historical_dispatch(plan,e,root,index,authority)
                if e.get("event")=="dispatch_intent":
                    spent[e["node_id"]]=spent.get(e["node_id"],0)+1
        view=project(plan,segment,require_bindings=True)["dispatches"]
        state=work_progress(plan,segment,[],False,review_context=(root,index,authority),state_only=True)
        running=sum(v["state"] in {"INTENT","DISPATCHED","CLAIMED","RUNNING","OUTCOME_UNKNOWN"} for v in view.values())
        nodes={n["id"]:n for n in plan["work_nodes"]}
        eligible=[i for i in state["ready"] if i not in view and nodes[i]["owner_role"] in READ_ROLES
                  and nodes[i]["operation_scope"] in {"read_only","independent_review"}
                  and not nodes[i].get("requires_submission") and not nodes[i].get("requires_idle_solver")
                  and spent.get(i,0)<nodes[i]["attempt_budget"]]
        return {"candidates":eligible[:max(0,3-running)],"status":"PROPOSED_ONLY",
                "journal_sha256":anchor.journal_sha256,"native_execution_authorized":False}

    def observe(self,plan,**kwargs):
        return observe_dispatch(plan,journal=self.journal,journal_anchor=self.anchor(),**kwargs)

    def recovery_candidate(self,**kwargs):
        return reconcile_owner(self.journal,**kwargs)


def host_dispatch_candidate(transaction,plan,event,*,host=None,**kwargs):
    """Do not call an external host until separately authorized; intent is
    recorded first, but the proposed host bridge remains blocked here."""
    if event.get("event")!="dispatch_intent":
        raise ValueError("dispatch intent required")
    if host is None:
        return {"status":"BLOCKED_HOST_ADAPTER","native_execution_authorized":False}
    # Host implementations must separately enforce actual admission and
    # checkpoint-linked intent/ack reconciliation. Never call an unknown API.
    return {"status":"HOST_ADAPTER_ENROLLMENT_REQUIRED","native_execution_authorized":False}


def cross_host_admission(*,local_domain,requested_domain,authority,binding):
    """No cross-machine locking service is enrolled; never grant remote write."""
    if local_domain!=requested_domain:
        return {"status":"BLOCKED_CROSS_HOST_COORDINATOR","authorized":False}
    require_verified(authority,"local_domain_binding",binding)
    return {"status":"LOCAL_SCOPE_ONLY","authorized":False}


def autonomy_metrics(events):
    """Observed pilot records only, no inferred native execution or TRACE used."""
    from collections import Counter
    unique={}
    for e in events:
        ident=e.get("event_id")
        if not isinstance(ident,str) or not ident:
            continue
        if ident in unique and unique[ident]!=e:
            raise ValueError("conflicting metric event")
        unique[ident]=e
    counts=Counter(e.get("event") for e in unique.values())
    return {"recorded_intents":counts["dispatch_intent"],"recorded_acks":counts["dispatch_ack"],
            "recorded_outputs":counts["dispatch_output"],"recorded_handoff_candidates":counts["handoff_adopted"],
            "recorded_failures":counts["dispatch_failed"],"unknown_outcomes":counts["dispatch_unknown"],
            "real_host_dispatch_count":None,"verified_trace_used_count":None,"native_success_count":None,
            "manual_interventions":None}
