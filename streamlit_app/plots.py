import plotly.graph_objects as go
from datetime import datetime, timedelta
from queries import execute_query, users_query, shops_query, events_query, request_response_logs_query, get_sankey_query
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_users_shops_plot():
    try:
        users_data = await execute_query(users_query)
        shops_data = await execute_query(shops_query)

        if not users_data or not shops_data:
            logger.warning("No data returned for users or shops query")
            return go.Figure(), [], []

        dates = [row['partition_key'] for row in users_data]
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
    except Exception as e:
        logger.error(f"Error creating users and shops plot: {e}")
        return go.Figure(), [], []

async def create_events_plot():
    try:
        events_data = await execute_query(events_query)

        if not events_data:
            logger.warning("No data returned from events query")
            return go.Figure(), []

        events_by_type = {}
        for row in events_data:
            event_type = row['event_type']
            event_date = row['event_date']
            count = row['count']

            if event_type not in events_by_type:
                events_by_type[event_type] = {'dates': [], 'counts': []}

            events_by_type[event_type]['dates'].append(event_date)
            events_by_type[event_type]['counts'].append(count)

        fig = go.Figure()

        for event_type, data in events_by_type.items():
            fig.add_trace(go.Scatter(
                x=data['dates'],
                y=data['counts'],
                mode='lines',
                name=event_type.capitalize(),
                line=dict(shape='linear')
            ))

        fig.update_layout(
            title='Event Counts by Date',
            xaxis_title='Date',
            yaxis_title='Count',
            legend_title='Event Type',
            xaxis=dict(
                tickformat="%Y-%m-%d",
                tickmode="auto",
                nticks=20,
            )
        )

        return fig, events_data
    except Exception as e:
        logger.error(f"Error creating events plot: {e}")
        return go.Figure(), []

async def create_status_code_plot():
    try:
        status_code_data = await execute_query(request_response_logs_query)

        if not status_code_data:
            logger.warning("No data returned from status code query")
            return go.Figure(), []

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
    except Exception as e:
        logger.error(f"Error creating status code plot: {e}")
        return go.Figure(), []

async def create_sankey_diagram():
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)  # Last 30 days

        sankey_query = get_sankey_query(start_date.isoformat(), end_date.isoformat())
        sankey_data = await execute_query(sankey_query)

        if not sankey_data:
            logger.warning("No data returned from Sankey query")
            return go.Figure(), []

        labels = []
        source = []
        target = []
        value = []
        label_to_index = {}

        for row in sankey_data:
            if row['source'] not in label_to_index:
                label_to_index[row['source']] = len(labels)
                labels.append(row['source'])
            if row['target'] not in label_to_index:
                label_to_index[row['target']] = len(labels)
                labels.append(row['target'])

            source.append(label_to_index[row['source']])
            target.append(label_to_index[row['target']])
            value.append(row['value'])

        fig = go.Figure(data=[go.Sankey(
            node = dict(
              pad = 15,
              thickness = 20,
              line = dict(color = "black", width = 0.5),
              label = labels,
              color = "blue"
            ),
            link = dict(
              source = source,
              target = target,
              value = value
          ))])

        fig.update_layout(title_text="User and Shop Activity Flow", font_size=10)

        return fig, sankey_data
    except Exception as e:
        logger.error(f"Error creating Sankey diagram: {e}")
        return go.Figure(), []