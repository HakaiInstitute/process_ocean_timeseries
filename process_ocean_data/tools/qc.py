"""
QC Module present a set of tools to manually qc data.
"""
import plotly.graph_objects as go
from ipywidgets import interactive, HBox, VBox, widgets


def manual_qc_interface(
    df, variable_list: list, flags: dict, review_flag: str = "_manual_flag"
):
    """
    Manually QC interface to manually QC oceanographic data, through a Jupyter notebook.
    :param df: DataFrame input to QC
    :param variable_list: Variable List to review
    :param flags: Flag convention used
    :param review_flag:
    """

    table_columns = list(df.filter(like="qartod_aggregate").columns)
    table_index = ["time"]
    table_columns = table_index + table_columns

    # Set Widgets of the interface
    yaxis = widgets.Dropdown(
        options=variable_list,
        value=variable_list[0],
        description="Y Axis:",
        disabled=False,
    )

    xaxis = widgets.Dropdown(
        options=["time", "depth"],
        value="time",
        description="X Axis:",
        disabled=False,
    )

    flag_selection = widgets.ToggleButtons(
        options=list(flags.keys()), description="Flag to apply:", disabled=False
    )

    apply_flag = widgets.Button(
        value=False,
        description="Apply Flag",
        disabled=False,
        button_style="success",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Apply Flag to select records.",
    )

    accordion = widgets.Accordion()
    accordion.selected_index = None

    # Create the initial plots
    # Plot widget with
    def _get_plots():
        """Generate plots based on the dataframe df, yaxis and xaxis values present
        within the respective widgets and flags in seperate colors"""
        plots = []
        for flag_name, flag_value in flags.items():
            df_flag = df.loc[df[yaxis.value + review_flag] == flag_value]
            plots += [
                go.Scattergl(
                    x=df_flag[xaxis.value],
                    y=df_flag[yaxis.value],
                    mode="markers",
                    name=flag_name,
                )
            ]
        return tuple(plots)

    f = go.FigureWidget(data=_get_plots(), layout=go.Layout(barmode="overlay"))
    f.update_layout(margin=dict(l=50, r=20, t=50, b=20))
    f.layout.xaxis.title = xaxis.value
    f.layout.yaxis.title = yaxis.value

    # Create a table FigureWidget that updates on selection from points in the scatter plot of f
    t = go.FigureWidget(
        [
            go.Table(
                header=dict(values=table_columns),
                cells=dict(values=[df[col] for col in table_columns]),
            )
        ]
    )
    t.update_layout(margin=dict(l=20, r=20, t=40, b=20))

    # Set the update to figure if the drop menu is changed
    figure_data = f.data

    def update_axes(xvar, yvar):
        """
        Update figure, based on x,y axis provided
        :param xvar:
        :param yvar:
        """
        kk = 0
        with f.batch_update():
            f.layout.xaxis.title = xvar
            f.layout.yaxis.title = yvar
            for plot in _get_plots():
                f.data[kk].x = plot.x
                f.data[kk].y = plot.y
                kk += 1

    def _get_selected_records():
        """Method to retrieve the x and y coordinates of the records selected with the plotly lasso tool."""
        xs = []
        ys = []
        for layer in figure_data:
            if layer["selectedpoints"]:
                xs += list(layer.x[list(layer["selectedpoints"])])
                ys += list(layer.y[list(layer["selectedpoints"])])
        return xs, ys

    def _get_selected_indexes(xs, ys):
        """Method to retrieve dataframe indexes of the selected x,y records shown on the figure."""
        is_indexes_selected = (
            df[[xaxis.value, yaxis.value]].apply(tuple, axis=1).isin(tuple(zip(xs, ys)))
        )
        return df.index[is_indexes_selected].tolist()

    def selection_fn(trace, points, selector):
        """Method to update the table showing the selected records."""
        if accordion.selected_index == 0:
            xs, ys = _get_selected_records()
            selected_indexes = _get_selected_indexes(xs, ys)
            if selected_indexes:
                t.data[0].cells.values = [
                    df.loc[selected_indexes][col] for col in table_columns
                ]

    def update_flag(_):
        """Tool triggered  when flag is applied to selected records."""
        # Retrieve selected records and flag column
        xs, ys = _get_selected_records()
        selected_indexes = _get_selected_indexes(xs, ys)
        flag_name = yaxis.value + review_flag

        # Create a column for the manual flag if it doesn't exist
        if flag_name not in df:
            df[flag_name] = flags["UNKNOWN"]

        print(
            "Apply {0} to {1} records in Flag column".format(
                flag_selection.value, len(selected_indexes), flag_name
            ),
            end="...",
        )
        # Update flag value within the dataframe
        df.loc[selected_indexes, flag_name] = flags[flag_selection.value]

        # Update figure with the new flags
        update_axes(xaxis.value, yaxis.value)
        print("Completed")

    # Setup the interaction between the different components
    axis_dropdowns = interactive(update_axes, yvar=yaxis, xvar=xaxis)
    for item in figure_data:
        item.on_selection(selection_fn)
    apply_flag.on_click(update_flag)

    # Create the interface
    plot_interface = HBox(axis_dropdowns.children)
    flag_interface = HBox((flag_selection, apply_flag))
    accordion.children = [t]
    accordion.set_title(0, "Selected Records Table")
    accordion.selected_index = None

    # Show me
    return VBox((VBox((plot_interface, flag_interface)), f, accordion))
