"""Optional real Hypothesis stateful tests; CI must install it, local absence is explicit."""
import pytest
pytest.importorskip('hypothesis')
from hypothesis import settings, given, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant as check_invariant
from scripts.verification_state import State, step, invariant, edge_invariant, ACTIONS
from scripts.check_multi_agent_v051 import admit
from test_multi_agent_v051 import fixture, NOW

class CoordinationMachine(RuleBasedStateMachine):
    def __init__(self): super().__init__(); self.s=State()
    @rule(action=st.sampled_from(ACTIONS))
    def act(self,action):
        t=step(self.s,action)
        if t is not None:
            assert edge_invariant(self.s,action,t)
            self.s=t
    @check_invariant()
    def valid(self): assert invariant(self.s)
TestCoordination=CoordinationMachine.TestCase
TestCoordination.settings=settings(max_examples=100,stateful_step_count=50,deadline=None)

@given(st.sampled_from(['active_veto','unresolved_operation']),st.one_of(st.none(),st.just(True),st.text(min_size=1)))
@settings(max_examples=100,deadline=None)
def test_non_false_blockers_never_admit(field,value):
    s=fixture();s[field]=value
    assert admit(s,NOW)['action']!='ADMISSION_CANDIDATE'
