import plotly.graph_objects as go
from datetime import datetime
from queries import execute_query, users_query, shops_query, events_query, request_response_logs_query

async def create_users_shops_plot():
    users_data = await execute_query(users_query)
    shops_data = await execute_query(shops_query)

    dates = [datetime.strptime(row['partition_key'], '%Y-%m-%d').date() for row in users_data]
    users_counts = [row['b'] for row in users_data]
    shops_counts = [row['b'] for row in shops_data]

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

async def create_events_plot():
    events_data = await execute_query(events_query)

    events_by_type = {}
    for row in events_data:
        event_type = row['event_type']
        hour = row['hour']
        count = row['count']

        if event_type not in events_by_type:
            events_by_type[event_type] = {'hours': [], 'counts': []}

        events_by_type[event_type]['hours'].append(hour)
        events_by_type[event_type]['counts'].append(count)

    fig = go.Figure()

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

async def create_status_code_plot():
    status_code_data = await execute_query(request_response_logs_query)

    status_codes = {}
    for row in status_code_data:
        status_code = row['status_code']
        minute = row['minute'].replace(second=0, microsecond=0)
        count = row['count']

        if status_code not in status_codes:
            status_codes[status_code] = {'minutes': [], 'counts': []}

        status_codes[status_code]['minutes'].append(minute)
        status_codes[status_code]['counts'].append(count)

    fig = go.Figure()

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
            nticks=15,
        )
    )

    return fig, status_code_data
