# import asyncio
# import plotly.io as pio
# from streamlit_app import create_users_shops_plot, create_events_plot, create_status_code_plot

# async def generate_plots():
#     # Generate the users/shops plot
#     users_shops_fig, users_data, shops_data = await create_users_shops_plot()
#     users_shops_plot_html = pio.to_html(users_shops_fig, full_html=False)
#     with open('app/templates/users_shops_plot.html', 'w') as f:
#         f.write(users_shops_plot_html)

#     # Generate the events plot
#     events_fig, events_data = await create_events_plot()
#     events_plot_html = pio.to_html(events_fig, full_html=False)
#     with open('app/templates/events_plot.html', 'w') as f:
#         f.write(events_plot_html)

#     # Generate the status code plot for the most recent hour
#     status_code_fig, status_code_data = await create_status_code_plot()
#     status_code_plot_html = pio.to_html(status_code_fig, full_html=False)
#     with open('app/templates/status_code_plot.html', 'w') as f:
#         f.write(status_code_plot_html)


