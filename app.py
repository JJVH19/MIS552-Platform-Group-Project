"""Person 1 owns the shared app; teammates implement importable feature functions."""
import streamlit as st
from features.retrieval import search
from scheduling_agent import create_plan, execute_plan
from booking_tools import propose_booking, confirm_booking, reject_booking
st.set_page_config(page_title='MeetFlow AI',page_icon='🏀',layout='wide')
st.title('🏀 MeetFlow AI')
st.caption('Synthetic basketball event and facility platform • Course prototype • Mock bookings only')
tabs=st.tabs(['Event Creator','Event Reviewer','Event Discovery','Booking Assistant','Event Coordination'])
with tabs[0]:
    st.subheader('Event Creator — Chapter 2')
    st.info('Person 2 will integrate generate_event(event_details) here. This tab is a placeholder, not a completed AI feature.')
with tabs[1]:
    st.subheader('Event Reviewer — Chapter 3')
    st.info('Person 2 will integrate review_event(event) here; generated event output will be passed directly to the reviewer.')
with tabs[2]:
    st.subheader('Event Discovery — Chapter 4')
    kind=st.radio('Search', ['courts','events'],horizontal=True)
    q=st.text_input('Describe what you need',value='indoor competitive basketball court in Tempe')
    method=st.selectbox('Retrieval', ['hybrid','keyword','semantic'])
    k=st.slider('Number of results',1,10,5)
    if q:
        with st.spinner('Ranking synthetic listings...'):
            output=search(q,kind,method,k)
        st.caption('Retrieval engine: '+output['mode'])
        if output['warning']:st.warning(output['warning'])
        for item in output['results']:
            with st.container(border=True):
                st.markdown('**'+item.get('name','Unnamed')+'**')
                st.caption('ID: '+item.get('venue_id',item.get('event_id',''))+' | '+item['city']+' | Score: '+str(item['score']))
                st.write(item.get('description',''))
                st.caption('Why matched: '+item['why_match'])
with tabs[3]:
    st.subheader('Booking Assistant — Chapter 5')
    st.caption('Fictional availability and mock bookings. Times are local to Arizona.')
    with st.form('scheduling_request'):
        city = st.text_input('City (optional)')
        venue_id = st.text_input('Venue ID (optional)')
        requested_date = st.text_input('Date (YYYY-MM-DD, optional)')
        start = st.text_input('Start time (HH:MM, optional)')
        end = st.text_input('End time (HH:MM, optional)')
        submitted = st.form_submit_button('Create search plan')
    if submitted:
        st.session_state.pop('scheduling_plan', None)
        st.session_state.pop('scheduling_result', None)
        st.session_state.pop('booking_result', None)
        try:
            st.session_state.scheduling_plan = create_plan({'city': city, 'venue_id': venue_id,
                'date': requested_date, 'start_time': start, 'end_time': end})
        except ValueError as exc:
            st.error(str(exc))
    if 'scheduling_plan' in st.session_state:
        plan = st.session_state.scheduling_plan
        st.write('Review the search plan and preferences:')
        for step in plan['steps']:
            st.write('- ' + step)
        st.json(plan['filters'])
        if st.button('Approve and search', key='approve_schedule'):
            try:
                st.session_state.pop('booking_result', None)
                st.session_state.scheduling_result = execute_plan(plan, approved=True)
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        if st.button('Reject plan', key='reject_schedule'):
            st.session_state.pop('scheduling_plan', None)
            st.session_state.pop('scheduling_result', None)
            st.session_state.pop('booking_result', None)
            st.rerun()
    if 'scheduling_result' in st.session_state:
        result = st.session_state.scheduling_result
        st.write('Search trace:', ' '.join(result['trace']))
        st.subheader('Agent timeline')
        for item in result['timeline']:
            with st.expander(f"Step {item['step']}: {item['tool']}", expanded=True):
                st.write(item['decision'])
                st.write('Arguments:')
                st.json(item['arguments'])
                st.write('Result:' if 'result' in item else 'Error:')
                st.json(item.get('result', item.get('error')))
        if result['status'] != 'completed':
            st.warning('Search did not complete: ' + result['status'])
        if result['results']:
            st.dataframe(result['results'], hide_index=True)
            st.subheader('Prepare a mock booking')
            slots = {item['slot_id']: item for item in result['results']}
            with st.form('booking_request'):
                selected = st.selectbox('Available slot', list(slots),
                    format_func=lambda key: f"{key} | {slots[key]['venue_name']} | {slots[key]['date']} {slots[key]['start_time']}-{slots[key]['end_time']}")
                event_id = st.text_input('Fictional event ID', value='EVT-001')
                create_booking = st.form_submit_button('Create booking proposal')
            if create_booking:
                slot = slots[selected]
                st.session_state.booking_result = propose_booking({**slot, 'event_id': event_id})
        elif result['status'] == 'completed':
            st.info('No matching available slots were found.')
    if 'booking_result' in st.session_state:
        booking = st.session_state.booking_result
        st.subheader('Mock booking proposal')
        if booking['proposal']:
            st.json(booking['proposal'])
        if booking['error']:
            st.error(booking['error'])
        st.write('Booking execution trace:')
        st.json(booking['trace'])
        if booking['status'] == 'pending_approval':
            st.info('Review this proposal. Booking approval is separate from search approval.')
            if st.button('Approve mock booking'):
                st.session_state.booking_result = confirm_booking(booking, approved=True)
                st.rerun()
            if st.button('Reject mock booking'):
                st.session_state.booking_result = reject_booking(booking)
                st.rerun()
        elif booking['status'] == 'approved':
            st.success('Mock booking approved for this session. It is not saved or reserved.')
        elif booking['status'] == 'rejected':
            st.info('Mock booking rejected.')
with tabs[4]:
    st.subheader('Event Coordination — Chapter 6')
    st.info('Person 4 will integrate coordinate_booking(proposal), multiple LLM agents, shared state and monitoring here.')
st.divider()
st.caption('Development note: Event Discovery and the fictional availability search are implemented; other features remain placeholders.')
