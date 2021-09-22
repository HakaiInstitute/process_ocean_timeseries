"""
QC Module present a set of tools to manually qc data.
"""
from logging import disable
import plotly.graph_objects as go
from ipywidgets import interactive, HBox, VBox, widgets
from IPython.display import display
import xarray as xr
from xarray.core.dataset import Dataset

flag_conventions = {
    "QARTOD": {
        1: {
            "Meaning": "GOOD",
            "Description": "Data have passed critical real-time quality control tests and are deemed "
            "adequate for use as preliminary data.",
            "Value": 1,
            "Color": "#2ECC40",
        },
        2: {
            "Meaning": "UNKNOWN",
            "Description": "Data have not been QC-tested, or the information on quality is not available.",
            "Value": 2,
            "Color": "#FFDC00",
        },
        3: {
            "Meaning": "SUSPECT",
            "Description": "Data are considered to be either suspect or of high interest to data providers and users. "
            "They are flagged suspect to draw further attention to them by operators.",
            "Value": 3,
            "Color": "#FF851B",
        },
        4: {
            "Meaning": "FAIL",
            "Description": "Data are considered to have failed one or more critical real-time QC checks. "
            "If they are disseminated at all, it should be readily apparent that they "
            "are not of acceptable quality.",
            "Value": 4,
            "Color": "#FF4136",
        },
        9: {
            "Meaning": "MISSING",
            "Description": "Data are missing; used as a placeholder.",
            "Value": 9,
            "Color": "#85144b",
        },
    },
    "HAKAI": {
        "ADL": {
            "Description": "Value was above the established detection limit of the sensor",
            "Meaning": "Above detection limit",
            "Value": "ADL",
            "Color": "#2ECC40",
        },
        "AR": {
            "Description": "Value above a specified upper limit",
            "Meaning": "Above range",
            "Value": "AR",
            "Color": "#2ECC40",
        },
        "AV": {
            "Description": "Has been reviewed and looks good",
            "Meaning": "Accepted value",
            "Value": "AV",
            "Color": "#2ECC40",
        },
        "BDL": {
            "Description": "Value was below the established detection limit of the sensor",
            "Meaning": "Below detection limit",
            "Value": "BDL",
            "Color": "#00ffff",
        },
        "BR": {
            "Description": "Value below a specified lower limit",
            "Meaning": "Below range",
            "Value": "BR",
            "Color": "#2ECC40",
        },
        "CD": {
            "Description": "Sensor needs to be sent back to the manufacturer for calibration",
            "Meaning": "Calibration due",
            "Value": "CD",
            "Color": "#2ECC40",
        },
        "CE": {
            "Description": "Value was collected with a sensor that is past due for calibration",
            "Meaning": "Calibration expired",
            "Value": "CE",
            "Color": "#2ECC40",
        },
        "EV": {
            "Description": "Value has been estimated",
            "Meaning": "Estimated value",
            "Value": "EV",
            "Color": "#2ECC40",
        },
        "IC": {
            "Description": "One or more non‐sequential date/time values",
            "Meaning": "Invalid chronology",
            "Value": "IC",
            "Color": "#2ECC40",
        },
        "II": {
            "Description": "Value was inconsistent with another related measurement",
            "Meaning": "Internal inconsistency",
            "Value": "II",
            "Color": "#2ECC40",
        },
        "LB": {
            "Description": "Sensor battery dropped below a threshold",
            "Meaning": "Low battery",
            "Value": "LB",
            "Color": "#2ECC40",
        },
        "MV": {
            "Description": "No measured value available because of equipment failure, etc.",
            "Meaning": "Missing value",
            "Value": "MV",
            "Color": "#FFDC00",
        },
        "PV": {
            "Description": "Repeated value for an extended period",
            "Meaning": "Persistent value",
            "Value": "PV",
            "Color": "#2ECC40",
        },
        "SE": {
            "Description": "Value much greater than the previous value, resulting in an unrealistic slope",
            "Meaning": "Slope exceedance",
            "Value": "SE",
            "Color": "#2ECC40",
        },
        "SI": {
            "Description": "Value greatly differed from values collected from nearby sensors",
            "Meaning": "Spatial inconsistency",
            "Value": "SI",
            "Color": "#2ECC40",
        },
        "SVC": {
            "Description": "Value appears to be suspect, use with caution",
            "Meaning": "Suspicious value - caution",
            "Value": "SVC",
            "Color": "#FF851B",
        },
        "SVD": {
            "Description": "Value is clearly suspect, recommend discarding",
            "Meaning": "Suspicious value - reject",
            "Value": "SVD",
            "Color": "#FF4136",
        },
        "NaN": {
            "Description": "No value available",
            "Meaning": "Not available",
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


def compare_flags(flags, convention=None, flag_priority=None):
    """
    General method that compare flags from the different flag conventions
    present in the flag_conventions dictionary by apply the priority list which is ordered from  the
    least to most prioritized flag.

    """
    if convention and convention in flag_conventions:
        flag_priority = flag_conventions["priority"][convention]

    record_flag = None
    for flag in flag_priority:
        if flag in flags:
            record_flag = flag
    return record_flag


def manual_qc_interface(
    df,
    variable_list: list,
    flags: dict or str,
    review_flag: str = "_review_flag",
    comment_column: str = "_review_comment",
    default_flag=None,
):
    """
    Manually QC interface to manually QC oceanographic data, through a Jupyter notebook.
    :param default_flag:
    :param comment_column:
    :param df: DataFrame input to QC
    :param variable_list: Variable List to review
    :param flags: Flag convention used
    :param review_flag:
    """
    #     # Generate a copy of the provided dataframe which will be use for filtering and plotting data|
    #     df_temp = df

    # If xarray convert to a dataframe to run the tool
    if isinstance(df, xr.Dataset):
        is_xarray_input = True
        ds = df
        df = ds.to_dataframe()
        index_names = df.index.names
        df = df.reset_index()

        # Add a specific button to update dataset from dataframe
        update_dataset_button = widgets.Button(
            value=False,
            description="Update Dataset Flags",
            disable=False,
            button_style="success",
        )
    else:
        is_xarray_input = False
        update_dataset = None

    # Retrieve Flag Convention
    if type(flags) is str:
        flag_convention = flags
        flags = flag_conventions[flags]
        flag_descriptor = f"{flag_convention}\n" + "\n".join(
            [
                f"{key} = {item['Meaning']}"
                for key, item in flag_conventions[flag_convention].items()
            ]
        )

    else:
        flag_descriptor = "\n".join([f"{key} = {item}" for key, item in flags.items()])

    # Set Widgets of the interface
    yaxis = widgets.Dropdown(
        options=variable_list,
        value=variable_list[0],
        description="Y Axis:",
        disabled=False,
    )

    xaxis = widgets.Dropdown(
        options=["depth", "time"],
        value="time",
        description="X Axis:",
        disabled=False,
    )

    filter_by = widgets.Text(
        value=None,
        description="Filter by",
        placeholder="ex: 20<depth<30",
        disabled=False,
    )

    filter_by_result = filter_by_result = widgets.HTML(
        value="{0} records available".format(len(df)),
    )

    apply_filter = widgets.Button(
        value=False,
        description="Apply Filter",
        disabled=False,
        button_style="success",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Apply Filter to the full dataset.",
    )

    flag_selection = widgets.Dropdown(
        options=list(flags.keys()), description=flag_descriptor, disabled=False
    )
    flag_comment = widgets.Textarea(
        value="",
        placeholder="Add review comment",
        description="Comment:",
        disabled=False,
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

    show_selection = widgets.Button(
        value=False,
        description="Show Selection",
        disabled=False,
        button_style="success",  # 'success', 'info', 'warning', 'danger' or ''
        tooltip="Present selected records in table.",
    )

    selected_table = widgets.Output()

    def get_filtered_data(df):
        """Apply query if available otherwise give back the full dataframe"""
        try:
            return df.query(filter_by.value)
        except ValueError:
            return df

    # Create the initial plots
    # Plot widget with
    def _get_plots():
        """Generate plots based on the dataframe df, yaxis and xaxis values present
        within the respective widgets and flags in seperate colors"""
        plots = []
        for flag_name, flag_value in flags.items():
            if type(flag_value) is dict and "Color" in flag_value:
                flag_color = flag_value["Color"]
                flag_meaning = flag_value["Meaning"]
            else:
                flag_color = flag_value
                flag_meaning = flag_value

            df_temp = get_filtered_data(df)

            df_flag = df_temp.loc[df_temp[yaxis.value + review_flag] == flag_name]
            plots += [
                go.Scattergl(
                    x=df_flag[xaxis.value],
                    y=df_flag[yaxis.value],
                    mode="markers",
                    name=flag_meaning,
                    marker={"color": flag_color, "opacity": 1},
                )
            ]

        return tuple(plots)

    # Initialize Figure Widget and layout
    f = go.FigureWidget(data=_get_plots(), layout=go.Layout(barmode="overlay"))
    f.update_layout(margin=dict(l=50, r=20, t=50, b=20))
    f.layout.xaxis.title = xaxis.value
    f.layout.yaxis.title = yaxis.value
    f.layout.title = "Review"
    f.update_layout(
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )

    # Set the update to figure if the drop menu is changed
    figure_data = f.data

    def update_filter(query_string=None):
        """Update filter report below the filter_by cell"""
        df_temp = get_filtered_data(df)

        if len(df_temp) == 0:
            # Give a message back saying no match and don't change anything else
            filter_by_result.value = "<p style='color:red;'>0 records found</p>"
        else:
            # Update text back and update plot with selection
            filter_by_result.value = "{0} records found".format(len(df_temp))

    def update_figure(_):
        """Update figure with present x and y items in menu"""
        update_axes(xaxis.value, yaxis.value)

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
        df_temp = get_filtered_data(df)
        is_indexes_selected = (
            df_temp[[xaxis.value, yaxis.value]]
            .apply(tuple, axis=1)
            .isin(tuple(zip(xs, ys)))
        )
        return df_temp.index[is_indexes_selected].tolist()

    def selection_fn(_):
        """Method to update the table showing the selected records."""
        xs, ys = _get_selected_records()
        selected_indexes = _get_selected_indexes(xs, ys)
        if selected_indexes:
            with selected_table:
                selected_table.clear_output()
                display(df.loc[selected_indexes])

    def update_flag_in_dataframe(_):
        """Tool triggered  when flag is applied to selected records."""
        # Retrieve selected records and flag column
        xs, ys = _get_selected_records()
        selected_indexes = _get_selected_indexes(xs, ys)
        flag_name = yaxis.value + review_flag
        comment_name = yaxis.value + comment_column

        # Create a column for the manual flag if it doesn't exist
        if flag_name not in df:
            df[flag_name] = default_flag
        # Print below the interface what's happening
        print(
            "Apply {0} to {1} records to {2}".format(
                flag_selection.value, len(selected_indexes), flag_name
            ),
            end="",
        )
        if flag_comment.value:
            print(" and add comment: {0}".format(flag_comment.value), end="")
        print(" ... ", end="")

        # Update flag value within the data frame
        df.loc[selected_indexes, flag_name] = flag_selection.value

        # Update comment
        if flag_comment.value:
            df.loc[selected_indexes, comment_name] = flag_comment.value

        # Update figure with the new flags
        update_figure(True)
        print("Completed")

    def update_dataset(_):
        """
        If xarray dataset provided, a button is added to the interface to update
        any changes made to flag data back in the xarray dataset.
        """
        print("Update Flags: ")
        for col in df.filter(like=review_flag).columns:
            print(col, end=": ")
            temp = ds[col].copy()
            ds[col] = df[col].set_index(index_names).to_xarray()
            ds[col].attrs = temp.attrs
            print("Done")

    # Setup the interaction between the different components
    axis_dropdowns = interactive(update_axes, yvar=yaxis, xvar=xaxis)
    show_selection.on_click(selection_fn)
    apply_filter.on_click(update_figure)
    apply_flag.on_click(update_flag_in_dataframe)
    filter_data = interactive(update_filter, query_string=filter_by)
    update_dataset_button.on_click(update_dataset)

    # Create the interface layout
    plot_interface = VBox(axis_dropdowns.children)
    flag_interface = VBox(
        (flag_selection, flag_comment, apply_flag, update_dataset_button),
        layout={"align_items": "flex-end"},
    )
    filter_by_interface = VBox(
        (filter_by, filter_by_result), layout={"align_items": "flex-end"}
    )
    filter_interface = HBox((filter_by_interface, apply_filter))
    upper_menu_left = VBox((plot_interface, filter_interface))
    upper_menu = HBox(
        (upper_menu_left, flag_interface), layout={"justify_content": "space-between"}
    )
    selection_table = VBox((show_selection, selected_table))

    # Set output
    if is_xarray_input:
        output_data = ds
    else:
        output_data = df

    return output_data, VBox(
        (
            upper_menu,
            f,
            selection_table,
        )
    )


def stack_dataframe_variables(
    df,
    by: list,
    stack_name: str,
    result_name: str,
    keep: list = None,
):
    df_to_stack = df.copy()
    if keep is None:
        keep = set(df.columns) - by

    # Stack given variables
    df_stacked = df_to_stack.set_index(keep)[by].stack()

    # Reset indexes and rename the group of stacked values and the resulting stacked column
    df_stacked.index.names = list(df_stacked.index.names[:-1]) + [stack_name]
    df_stacked = df_stacked.reset_index()
    df_stacked.columns = list(df_stacked.columns[:-1]) + [result_name]
    return df_stacked
