def plot_fuel_litres_over_time() -> go.Figure:
    df = get_fuel_litres_over_time(str(st.user.sub))
    fig = px.line(
        data_frame=df,
        x="entry_datetime",
        y="fuel_filled",
        color="vehicle",
        hover_name="vehicle",
        hover_data={
            "entry_datetime": "|%b %d, %Y",
            "fuel_filled": ":.2f",
        },
        markers=True,
        title="Fuel Filled Over Time",
        subtitle="Are you consistent with how much fuel you fill at a time?",
    )
    fig.update_layout(
        showlegend=True,
        # margin={"t": 10},
        xaxis={"title": {"text": "Date"}},
        yaxis={"title": {"text": "Fuel (L)"}},
    )
    return fig


def st_plot_fuel_litres_over_time():
    st.plotly_chart(
        plot_fuel_litres_over_time(),
        width="stretch",
        height=350,
        config={"displayModeBar": False},
    )
