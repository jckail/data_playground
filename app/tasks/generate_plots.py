import plotly.io as pio
from streamlit_app import create_users_shops_plot, create_events_plot

def generate_plots():
    # Generate the users/shops plot
    users_shops_fig, users_data, shops_data = create_users_shops_plot()
    users_shops_plot_html = pio.to_html(users_shops_fig, full_html=False)
    with open('app/templates/users_shops_plot.html', 'w') as f:
        f.write(users_shops_plot_html)

    # Generate the events plot
    events_fig, events_data = create_events_plot()
    events_plot_html = pio.to_html(events_fig, full_html=False)
    with open('app/templates/events_plot.html', 'w') as f:
        f.write(events_plot_html)
