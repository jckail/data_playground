import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from app.database import execute_query
import requests

# Queries
users_query = "SELECT partition_key, count(*) a, count(distinct id) b FROM users group by partition_key order by 1;"
shops_query = "SELECT partition_key, count(*) a, count(distinct id) b FROM shops group by partition_key order by 1;"

def generate_fake_data():
    response = requests.post("http://0.0.0.0:8000/trigger_fake_data")
    return response.json()["message"]

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

# Streamlit app
st.title('Users and Shops Data Visualization')

st.plotly_chart(fig)

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

# Button to go to FastAPI page
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