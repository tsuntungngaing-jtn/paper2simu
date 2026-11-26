---- MODULE Coordination ----
EXTENDS Integers, TLC
VARIABLE s
Init == s = [writer |-> "NONE", job |-> "IDLE", rev |-> 0, review |-> -1,
             solved |-> -1, accepted |-> -1, veto |-> FALSE, budget |-> 2,
             submits |-> 0, closed |-> FALSE]
Idle == s.job = "IDLE"
HasWriter == s.writer # "NONE"
Current == s.review = s.rev
Open == ~s.closed
Lease(w) == /\ Open /\ ~HasWriter /\ Idle /\ s.budget > 0
            /\ s' = [s EXCEPT !.writer = w]
Release == /\ Open /\ HasWriter /\ Idle
            /\ s' = [s EXCEPT !.writer = "NONE", !.review = -1]
Review == /\ Open /\ HasWriter /\ Idle /\ ~s.veto /\ s.budget > 0
           /\ s' = [s EXCEPT !.review = s.rev]
Veto == /\ Open /\ ~s.veto
        /\ s' = [s EXCEPT !.veto = TRUE, !.review = -1, !.accepted = -1]
ClearVeto == /\ Open /\ s.veto /\ Idle
             /\ s' = [s EXCEPT !.veto = FALSE, !.review = -1]
Submit == /\ Open /\ HasWriter /\ Idle /\ Current /\ ~s.veto /\ s.budget > 0 /\ s.submits < 2
          /\ s' = [s EXCEPT !.job = "RUNNING", !.submits = @+1,
                    !.review = -1, !.solved = -1, !.accepted = -1]
Disconnect == /\ Open /\ s.job \in {"IDLE", "RUNNING"}
              /\ s' = [s EXCEPT !.job = IF @ = "RUNNING" THEN "UNKNOWN_RUNNING" ELSE "UNKNOWN_IDLE",
                        !.review = -1, !.accepted = -1]
ReconcileIdle == /\ Open /\ s.job = "UNKNOWN_IDLE"
                 /\ s' = [s EXCEPT !.job = "IDLE"]
ReconcileRunning == /\ Open /\ s.job = "UNKNOWN_RUNNING"
                    /\ s' = [s EXCEPT !.job = "RUNNING"]
Complete == /\ Open /\ s.job = "RUNNING"
             /\ s' = [s EXCEPT !.job = "IDLE", !.solved = s.rev, !.review = -1]
Edit == /\ Open /\ HasWriter /\ Idle /\ Current /\ ~s.veto /\ s.budget > 0 /\ s.rev < 2
        /\ s' = [s EXCEPT !.rev = @+1, !.review = -1, !.solved = -1, !.accepted = -1]
Accept == /\ Open /\ Idle /\ s.solved = s.rev /\ ~s.veto
          /\ s' = [s EXCEPT !.accepted = s.rev]
Tick == /\ Open /\ s.budget > 0
        /\ s' = [s EXCEPT !.budget = @-1, !.review = IF s.budget = 1 THEN -1 ELSE @]
CloseCase == /\ Open /\ s.budget = 0 /\ Idle
             /\ s' = [s EXCEPT !.closed = TRUE, !.writer = "NONE", !.review = -1]
Next == \/ Lease("a") \/ Lease("b") \/ Release \/ Review \/ Veto \/ ClearVeto
        \/ Submit \/ Disconnect \/ ReconcileIdle \/ ReconcileRunning \/ Complete
        \/ Edit \/ Accept \/ Tick \/ CloseCase
Spec == Init /\ [][Next]_s
TypeOK == /\ s.writer \in {"NONE", "a", "b"}
          /\ s.job \in {"IDLE", "RUNNING", "UNKNOWN_RUNNING", "UNKNOWN_IDLE"}
          /\ s.rev \in 0..2 /\ s.review \in -1..2 /\ s.solved \in -1..2
          /\ s.accepted \in -1..2 /\ s.budget \in 0..2 /\ s.submits \in 0..2
          /\ s.veto \in BOOLEAN /\ s.closed \in BOOLEAN
Fresh == /\ s.review \in {-1,s.rev} /\ s.solved \in {-1,s.rev}
AcceptValid == s.accepted = -1 \/ (s.accepted = s.rev /\ s.solved = s.rev /\ Idle /\ ~s.veto)
ActiveWriter == s.job \in {"RUNNING","UNKNOWN_RUNNING"} => HasWriter
ClosedValid == s.closed => (Idle /\ s.budget = 0 /\ ~HasWriter)
NoIllegalSubmit == [][s'.submits > s.submits => (Idle /\ HasWriter /\ Current /\ ~s.veto /\ s.budget > 0)]_s
NoBudgetReset == [][s'.budget <= s.budget]_s
====
