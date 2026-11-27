import hashlib
import pytest
from server.trace_evidence import consumption_view
from server.deployment_identity import verify, REQUIRED


def trace(disposition="ADOPTED"):
    ctx = dict(task_id="t",case_id="c",plan_revision="r",task_kind="paper",paper_id="P1",
               artifact_sha256="a"*64,source_receipt_id="receipt")
    a = dict(ctx,event="artifact_observed",event_id="p",producer_step="s1")
    b = dict(ctx,event="consumer_disposition",event_id="d",producer_event_id="p",
             consumer_step="s2",consumer_input_sha256="a"*64,disposition=disposition)
    return a,b


@pytest.mark.parametrize("state,count",[("ADOPTED",1),("HOLD",0),("REJECTED",0),("UNKNOWN",0)])
def test_explicit_use(state,count):
    a,b = trace(state)
    assert len(consumption_view([a,b,b])["used"]) == count
    assert consumption_view([a])["used"] == []


@pytest.mark.parametrize("change",[{"paper_id":"P2"},{"artifact_sha256":"b"*64},
                                   {"consumer_input_sha256":"b"*64},{"consumer_step":"s1"}])
def test_bad_use(change):
    a,b = trace()
    with pytest.raises(ValueError):
        consumption_view([a,dict(b,**change)])


def test_fingerprint(tmp_path):
    (tmp_path/"source").write_bytes(b"approved")
    h = hashlib.sha256(b"approved").hexdigest()
    m = dict(display_version="0.6.3",commit="a"*40,groups={k:{"source":h} for k in REQUIRED})
    assert verify(m,tmp_path,"a"*40)["status"] == "DECLARED_FILES_MATCH"
    (tmp_path/"source").write_bytes(b"changed")
    assert verify(m,tmp_path,"a"*40)["status"] == "MISMATCH"
    assert verify(m,tmp_path,"b"*40)["status"] == "COMMIT_MISMATCH"
