"""
QC Module present a set of tools to manually qc data.
"""
import plotly.graph_objects as go
from ipywidgets import interactive, HBox, VBox, widgets

flag_conventions = {
    "QARTOD": {
        "GOOD": {
            "Name": "GOOD",
            "Description": "Data have passed critical real-time quality control tests and are deemed "
            "adequate for use as preliminary data.",
            "Value": 1,
            "Color": "#2ECC40",
        },
        "UNKNOWN": {
            "Name": "UNKNOWN",
            "Description": "Data have not been QC-tested, or the information on quality is not available.",
            "Value": 2,
            "Color": "#FFDC00",
        },
        "SUSPECT": {
            "Name": "SUSPECT",
            "Description": "Data are considered to be either suspect or of high interest to data providers and users. "
            "They are flagged suspect to draw further attention to them by operators.",
            "Value": 3,
            "Color": "#FF851B",
        },
        "FAIL": {
            "Name": "FAIL",
            "Description": "Data are considered to have failed one or more critical real-time QC checks. "
            "If they are disseminated at all, it should be readily apparent that they "
            "are not of acceptable quality.",
            "Value": 4,
            "Color": "#FF4136",
        },
        "MISSING": {
            "Name": "MISSING",
            "Description": "Data are missing; used as a placeholder.",
            "Value": 9,
            "Color": "#85144b",
        },
    },
    "HAKAI": {
        "ADL": {
            "Description": "Value was above the established detection limit of the sensor",
            "Name": "Above detection limit",
            "Value": "ADL",
            "Color": "#2ECC40",
        },
        "AR": {
            "Description": "Value above a specified upper limit",
            "Name": "Above range",
            "Value": "AR",
            "Color": "#2ECC40",
        },
        "AV": {
            "Description": "Has been reviewed and looks good",
            "Name": "Accepted value",
            "Value": "AV",
            "Color": "#2ECC40",
        },
        "BDL": {
            "Description": "Value was below the established detection limit of the sensor",
            "Name": "Below detection limit",
            "Value": "BDL",
            "Color": "#2ECC40",
        },
        "BR": {
            "Description": "Value below a specified lower limit",
            "Name": "Below range",
            "Value": "BR",
            "Color": "#2ECC40",
        },
        "CD": {
            "Description": "Sensor needs to be sent back to the manufacturer for calibration",
            "Name": "Calibration due",
            "Value": "CD",
            "Color": "#2ECC40",
        },
        "CE": {
            "Description": "Value was collected with a sensor that is past due for calibration",
            "Name": "Calibration expired",
            "Value": "CE",
            "Color": "#2ECC40",
        },
        "EV": {
            "Description": "Value has been estimated",
            "Name": "Estimated value",
            "Value": "EV",
            "Color": "#2ECC40",
        },
        "IC": {
            "Description": "One or more non‐sequential date/time values",
            "Name": "Invalid chronology",
            "Value": "IC",
            "Color": "#2ECC40",
        },
        "II": {
            "Description": "Value was inconsistent with another related measurement",
            "Name": "Internal inconsistency",
            "Value": "II",
            "Color": "#2ECC40",
        },
        "LB": {
            "Description": "Sensor battery dropped below a threshold",
            "Name": "Low battery",
            "Value": "LB",
            "Color": "#2ECC40",
        },
        "MV": {
            "Description": "No measured value available because of equipment failure, etc.",
            "Name": "Missing value",
            "Value": "MV",
            "Color": "#FFDC00",
        },
        "PV": {
            "Description": "Repeated value for an extended period",
            "Name": "Persistent value",
            "Value": "PV",
            "Color": "#2ECC40",
        },
        "SE": {
            "Description": "Value much greater than the previous value, resulting in an unrealistic slope",
            "Name": "Slope exceedance",
            "Value": "SE",
            "Color": "#2ECC40",
        },
        "SI": {
            "Description": "Value greatly differed from values collected from nearby sensors",
            "Name": "Spatial inconsistency",
            "Value": "SI",
            "Color": "#2ECC40",
        },
        "SVC": {
            "Description": "Value appears to be suspect, use with caution",
            "Name": "Suspicious value - caution",
            "Value": "SVC",
            "Color": "#FF851B",
        },
        "SVD": {
            "Description": "Value is clearly suspect, recommend discarding",
            "Name": "Suspicious value - reject",
            "Value": "SVD",
            "Color": "#FF4136",
        },
        "NaN": {
            "Description": "No value available",
            "Name": "Not available",
            "Value": "NaN",
            "Color": "#85144b",
        },
    },
    "priority": {
        "HAKAI": [
            "NaN",
            "MV",
            "AV",
            "CD",
            "CE",
            "IC",
            "LB",
            "ADL",
            "AD",
            "BDL",
            "EV",
            "BR",
            "II",
            "SI",
            "SE",
            "PV",
            "SVC",
            "SVD",
        ],
        "QARTOD": [9, 2, 1, 3, 4],
    },
    "mapping": {"QARTOD-HAKAI": {1: "AV", 2: "MV", 3: "SVC", 4: "SVD", 9: "NaN"}},
}

def manual_qc_interface(
    df, variable_list: list, flags: dict, review_flag: str = "_review_flag"
):
    """
    Manually QC interface to manually QC oceanographic data, through a Jupyter notebook.
    :param df: DataFrame input to QC
    :param variable_list: Variable List to review
    :param flags: Flag convention used
    :param review_flag:
    """

    # Identify variables to present in table (qc data and associated values)
    table_flag_columns = list(df.filter(regex="qartod|season|review").columns)
    table_index = ["time"]
    table_columns = table_index + table_flag_columns

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
    # t.update_layout(margin=dict(l=20, r=20, t=40, b=20))

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
