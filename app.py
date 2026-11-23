"""Person 1 owns the shared app; teammates implement importable feature functions."""
import streamlit as st
from features.retrieval import search
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
    st.info('Person 3 will integrate propose_booking(request), mock tool calls, trace and approval here.')
with tabs[4]:
    st.subheader('Event Coordination — Chapter 6')
    st.info('Person 4 will integrate coordinate_booking(proposal), multiple LLM agents, shared state and monitoring here.')
st.divider()
st.caption('Development note: Five page shells exist; only Event Discovery is implemented by this starter.')
