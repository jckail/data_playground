import asyncio
from threading import Thread
from asyncio import run_coroutine_threadsafe
import streamlit as st
import os
import plotly.io as pio
from plots import create_users_shops_plot, create_events_plot, create_status_code_plot, create_sankey_diagram

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    sankey_task = create_sankey_diagram()
    
    results = await asyncio.gather(
        users_shops_task, events_task, status_code_task, sankey_task,
        return_exceptions=True
    )
    
    return results

def app_logic():
    try:
        # Fetch data every time the page is refreshed
        results = run_async(main())

        # Streamlit app
        st.title('Users, Shops, Event, and Status Code Data Visualization')

        plot_functions = [
            ('Users and Shops Count Over Time', create_users_shops_plot),
            ('Event Counts Over Time', create_events_plot),
            ('Status Code Counts Per Minute (Last Hour)', create_status_code_plot),
            ('User and Shop Activity Flow (Last 30 Days)', create_sankey_diagram)
        ]

        for i, (title, _) in enumerate(plot_functions):
            result = results[i]
            if isinstance(result, Exception):
                st.error(f"Error occurred while creating {title}: {str(result)}")
            else:
                st.subheader(title)
                if i == 0:  # Users and Shops plot
                    fig, users_data, shops_data = result
                    if users_data and shops_data:
                        st.plotly_chart(fig)
                        st.write('Users Data:')
                        st.write(users_data)
                        st.write('Shops Data:')
                        st.write(shops_data)
                    else:
                        st.warning(f"No data available for {title}")
                else:
                    fig, data = result
                    if data:
                        st.plotly_chart(fig)
                        st.write(f'Raw data for {title}:')
                        st.write(data)
                    else:
                        st.warning(f"No data available for {title}")

    except Exception as e:
        logger.error(f"An error occurred in the Streamlit app: {e}")
        st.error("An error occurred while generating the visualizations. Please try again later.")

if __name__ == "__main__":
    app_logic()