import asyncio
from threading import Thread
from asyncio import run_coroutine_threadsafe
import streamlit as st
import os
import plotly.io as pio
from plots import create_users_shops_plot, create_events_plot, create_status_code_plot

# Utility to create and manage the event loop in a separate thread
@st.cache_resource(show_spinner=False)
def create_loop():
    loop = asyncio.new_event_loop()
    thread = Thread(target=loop.run_forever)
    thread.start()
    return loop, thread

# Function to run async operations in the separate event loop
def run_async(coroutine):
    return run_coroutine_threadsafe(coroutine, st.session_state.event_loop).result()

# Ensure the loop is created once and cached
if 'event_loop' not in st.session_state:
    st.session_state.event_loop, worker_thread = create_loop()

# Main logic of your application
async def main():
    users_shops_task = create_users_shops_plot()
    events_task = create_events_plot()
    status_code_task = create_status_code_plot()
    
    users_shops_result, events_result, status_code_result = await asyncio.gather(
        users_shops_task, events_task, status_code_task
    )
    
    return users_shops_result, events_result, status_code_result

def app_logic():
    users_shops_result, events_result, status_code_result = run_async(main())

    # Unpack the results
    users_shops_fig, users_data, shops_data = users_shops_result
    events_fig, events_data = events_result
    status_code_fig, status_code_data = status_code_result

    # Generate static HTML for each plot
    users_shops_html = pio.to_html(users_shops_fig, full_html=False)
    events_html = pio.to_html(events_fig, full_html=False)
    status_code_html = pio.to_html(status_code_fig, full_html=False)

    # Ensure the 'templates' directory exists
    os.makedirs('templates', exist_ok=True)

    # Save the plot HTML to files
    with open('templates/users_shops_plot.html', 'w') as f:
        f.write(users_shops_html)
    with open('templates/events_plot.html', 'w') as f:
        f.write(events_html)
    with open('templates/status_code_plot.html', 'w') as f:
        f.write(status_code_html)

    # Streamlit app
    st.title('Users, Shops, Event, and Status Code Data Visualization')

    # Display the users and shops plot
    st.subheader('Users and Shops Count Over Time')
    st.plotly_chart(users_shops_fig)

    # Display the events plot
    st.subheader('Event Counts Over Time')
    st.plotly_chart(events_fig)

    # Display the status code plot
    st.subheader('Status Code Counts Over Time')
    st.plotly_chart(status_code_fig)

    # Display raw data
    st.subheader('Raw Data')
    st.write('Users Data:')
    st.write(users_data)
    st.write('Shops Data:')
    st.write(shops_data)
    st.write('Events Data:')
    st.write(events_data)
    st.write('Status Code Data:')
    st.write(status_code_data)

if __name__ == "__main__":
    app_logic()
