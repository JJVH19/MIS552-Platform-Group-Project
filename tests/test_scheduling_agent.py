import pytest
from scheduling_agent import create_plan, execute_plan


def test_approval_and_matching():
    plan = create_plan({'venue_id': 'VEN-001', 'date': '2026-12-13',
                        'start_time': '11:00', 'end_time': '13:00'})
    with pytest.raises(PermissionError):
        execute_plan(plan)
    result = execute_plan(plan, approved=True)
    assert [slot['slot_id'] for slot in result['results']] == ['SLOT-0002']
    assert 'No booking was created.' in result['trace']
    assert [step['tool'] for step in result['timeline']] == [
        'find_facilities', 'find_slots', 'format_results']
    assert all('arguments' in step and 'result' in step for step in result['timeline'])


def test_unavailable_and_modified_plan():
    plan = create_plan({'venue_id': 'VEN-001', 'date': '2026-12-12'})
    assert execute_plan(plan, approved=True)['results'] == []
    plan['steps'].append('Make a booking')
    with pytest.raises(ValueError):
        execute_plan(plan, approved=True)


def test_invalid_times():
    with pytest.raises(ValueError):
        create_plan({'start_time': '12:00', 'end_time': '11:00'})


def test_step_limit_and_early_stop():
    plan = create_plan({'venue_id': 'VEN-001', 'date': '2026-12-13'})
    limited = execute_plan(plan, approved=True, max_steps=1)
    assert limited['status'] == 'step_limit_reached'
    assert len(limited['timeline']) == 1
    with pytest.raises(ValueError):
        execute_plan(plan, approved=True, max_steps=4)
    empty = execute_plan(create_plan({'venue_id': 'VEN-NO-SUCH-VENUE'}), approved=True)
    assert empty['status'] == 'completed'
    assert len(empty['timeline']) == 1
