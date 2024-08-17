import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from app.database import execute_query
import requests
import plotly.io as pio

# Queries
users_query = "SELECT partition_key, count(*) a, count(distinct id) b FROM users group by partition_key order by 1;"
shops_query = "SELECT partition_key, count(*) a, count(distinct id) b FROM shops group by partition_key order by 1;"
events_query = """
    SELECT event_time::timestamp::date AS event_date,
           date_trunc('hour', event_time) AS hour,
           event_type,
           count(distinct event_id) as count
    FROM global_events
    GROUP BY event_date, hour, event_type
    ORDER BY hour;
"""
request_response_logs_query = """
    WITH recent_hour AS (
        SELECT date_trunc('hour', MAX(event_time)) AS max_hour
        FROM request_response_logs
    )
    SELECT date_trunc('minute', event_time) AS minute,
           status_code,
           count(*) as count
    FROM request_response_logs, recent_hour
    WHERE event_time >= recent_hour.max_hour
      AND event_time < recent_hour.max_hour + INTERVAL '1 hour'
    GROUP BY minute, status_code
    ORDER BY minute;
"""

def generate_fake_data():
    response = requests.post("http://0.0.0.0:8000/trigger_fake_data")
    return response.json()["message"]

def create_users_shops_plot():
    # Execute queries
    users_data = execute_query(users_query)
    shops_data = execute_query(shops_query)

    # Process data for plotting
    dates = [datetime.strptime(row['partition_key'], '%Y-%m-%d').date() for row in users_data]
    users_counts = [row['b'] for row in users_data]
    shops_counts = [row['b'] for row in shops_data]

    # Create the plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(x=dates, y=users_counts, mode='lines', name='Users', line=dict(color='green')))
    fig.add_trace(go.Scatter(x=dates, y=shops_counts, mode='lines', name='Shops', line=dict(color='blue')))

    fig.update_layout(
        title='Users and Shops Count Over Time',
        xaxis_title='Date',
        yaxis_title='Count',
        legend_title='Entity Type',
    )

    return fig, users_data, shops_data

def create_events_plot():
    # Execute the events query
    events_data = execute_query(events_query)

    # Process events data for plotting
    events_by_type = {}
    for row in events_data:
        event_type = row['event_type']
        hour = row['hour']
        count = row['count']

        if event_type not in events_by_type:
            events_by_type[event_type] = {'hours': [], 'counts': []}

        events_by_type[event_type]['hours'].append(hour)
        events_by_type[event_type]['counts'].append(count)

    # Create the plot for events data
    fig = go.Figure()

    # Add traces for each event type
    for event_type, data in events_by_type.items():
        fig.add_trace(go.Scatter(
            x=data['hours'],
            y=data['counts'],
            mode='lines',
            name=event_type.capitalize(),
            line=dict(shape='linear')
        ))

    fig.update_layout(
        title='Event Counts Over Time',
        xaxis_title='Time (Hourly Intervals)',
        yaxis_title='Count',
        legend_title='Event Type',
        xaxis=dict(
            tickformat="%H:%M\n%b %d",
            tickmode="auto",
            nticks=20,
        )
    )

    return fig, events_data

def create_status_code_plot():
    # Execute the request_response_logs query
    status_code_data = execute_query(request_response_logs_query)

    # Process status code data for plotting
    status_codes = {}
    for row in status_code_data:
        status_code = row['status_code']
        minute = row['minute'].replace(second=0, microsecond=0)  # Ensure clean minute intervals
        count = row['count']

        if status_code not in status_codes:
            status_codes[status_code] = {'minutes': [], 'counts': []}

        status_codes[status_code]['minutes'].append(minute)
        status_codes[status_code]['counts'].append(count)

    # Check if the data was grouped correctly
    st.write('Processed Status Code Data:', status_codes)  # Debugging line to inspect processed data

    # Create the plot for status code data
    fig = go.Figure()

    # Add traces for each status code
    for status_code, data in status_codes.items():
        fig.add_trace(go.Scatter(
            x=data['minutes'],
            y=data['counts'],
            mode='lines',
            name=f"Status {status_code}",
            line=dict(shape='linear')
        ))

    fig.update_layout(
        title='Status Code Counts Per Minute for the Most Recent Hour',
        xaxis_title='Time (Minute Intervals)',
        yaxis_title='Count',
        legend_title='Status Code',
        xaxis=dict(
            tickformat="%H:%M",
            tickmode="linear",
            nticks=15,  # 60 minutes in the hour
        )
    )

    return fig, status_code_data



# Create the plots
users_shops_fig, users_data, shops_data = create_users_shops_plot()
events_fig, events_data = create_events_plot()
status_code_fig, status_code_data = create_status_code_plot()

# Generate static HTML for each plot
users_shops_html = pio.to_html(users_shops_fig, full_html=False)
events_html = pio.to_html(events_fig, full_html=False)
status_code_html = pio.to_html(status_code_fig, full_html=False)

# Save the plot HTML to files
with open('app/templates/users_shops_plot.html', 'w') as f:
    f.write(users_shops_html)
with open('app/templates/events_plot.html', 'w') as f:
    f.write(events_html)
with open('app/templates/status_code_plot.html', 'w') as f:
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

# Create two columns for buttons
col1, col2 = st.columns(2)

# Generate Fake Data button
if col1.button('Generate Fake Data'):
    message = generate_fake_data()
    st.write(message)

# Button to go to FastAPI page
if col2.button('Go to FastAPI Home'):
    js = f"window.open('http://0.0.0.0:8000', '_blank').focus();"
    html = f'<img src onerror="{js}">'
    st.components.v1.html(html, height=0)

# Button to go to FastAPI Docs
if col2.button('Go to FastAPI Docs'):
    js = f"window.open('http://0.0.0.0:8000/docs', '_blank').focus();"
    html = f'<img src onerror="{js}">'
    st.components.v1.html(html, height=0)

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
