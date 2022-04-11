import pandas as pd
import re
from datetime import datetime

import logging

logger = logging.getLogger(__name__)
onset_variables_mapping = {
    "#": "record_number",
    "Date Time": "time",
    "Temp": "temperature",
    "Intensity": "light_intensity",
    "Specific Conductance": "specific_conductance",
    "Low Range": "low_range",
    "EOF": "end_of_file",
    "End of File": "end_of_file",
    "Abs Pres Barom.": "barometric_pressure",
    "Abs Pres": "pressure",
    "Sensor Depth": "sensor_depth",
    "Turbidity": "turbidity",
    "Water Level": "water_level",
}

ignored_variables = [
    "record_number",
    "time",
    "button_up",
    "button_down",
    "host_connected",
    "end_of_file",
    "coupler_detached",
    "coupler_attached",
    "stopped",
    "started",
    "good_battery",
    "bad_battery",
    "host_connect",
    "batt",
    "low_power",
    "water_detect",
    "record",
    "",
]


def csv(
    path,
    output: str = "xarray",
    timezone: str = None,
    convert_units_to_si: bool = True,
    input_read_csv_kwargs: dict = {},
):

    """tidbit_csv parses the Onset Tidbit CSV format into a pandas dataframe

    Returns:
        df: data in pandas dataframe
        metadata: metadata dictionary
    """
    encoding = input_read_csv_kwargs.get("encoding", "UTF-8")
    csv_format = "Plot Title"
    with open(path, "r", encoding=encoding) as f:
        first_line = f.readline().replace("\n", "")
        if "Serial Number:" in first_line:
            # skip second empty line
            csv_format = "Serial Number"
            f.readline()  #
        # Read csv columns
        columns_line = f.readline()

    # Handle Date Time variable with timezone
    header_timezone = re.search("GMT\s*([\-\+\d\:]*)", columns_line)
    timezone = header_timezone[1] if header_timezone else ""
    time_variable = re.search('[^"]*Date Time[^"]*', columns_line)[0]
    # Inputs to pd.read_csv
    read_csv_kwargs = {
        "na_values": [" "],
        "infer_datetime_format": True,
        "parse_dates": [time_variable],
        "converters": {
            time_variable: lambda col: pd.to_datetime(col)
            .tz_localize(timezone)
            .tz_convert("UTC")
        },
        "index_col": "#" if "#" in columns_line else None,
        "header": 1,
        "memory_map": True,
        "encoding": encoding,
        "engine": "c",
    }

    read_csv_kwargs.update(input_read_csv_kwargs)
    ds = pd.read_csv(path, **read_csv_kwargs).to_xarray()

    ds.attrs = {"instrument_manufacturer": "Onset", "history": ""}
    # Parse header lines
    if timezone == None:
        timezone = re.search(
            "GMT\s*([\-\+\d\:]*)", [var for var in ds if "Date Time" in var][0]
        )

    if csv_format == "Plot Title":
        columns = ":".join([var for var in ds])
        ds.attrs.update(
            {
                "logger_sn": ",".join(set(re.findall("LGR S\/N\: (\d*)", columns))),
                "instrument_sn": ",".join(set(re.findall("SEN S\/N\: (\d*)", columns))),
                "lbl": ",".join(set(re.findall("lbl: (\d*)", columns))),
            }
        )
    elif csv_format == "Serial Number":
        ds.attrs.update(
            {"instrument_sn": set(re.findall("Serial Number\:(\d+)", first_line))}
        )

    # Rename variables
    original_columns = [var for var in ds]
    for var in ds:
        ds[var].attrs["original_column_name"] = var

    # Drop those components from the column names
    var_names_with_units = [
        re.sub("\s*\({0,1}(LGR|SEN) S\/N\: .*", "", item) for item in ds
    ]
    if csv_format == "Plot Title":
        plot_title = re.search("Plot Title\: (\w*)\,+", first_line)
        if plot_title:
            var_names_with_units = [
                re.sub("[^\(]*" + plot_title[1], "", col).strip()
                for col in var_names_with_units
            ]

    # Retrieve units from column names
    units = [
        re.split("\,|\(", item.replace(")", "").strip())[-1].strip()
        if re.search("\,|\(", item)
        else None
        for item in var_names_with_units
    ]
    for var, units in zip(original_columns, units):
        if units and "Date Time" not in var:
            ds[var].attrs["units"] = units

    # Generate variable names
    var_names = [re.split("\,|\(|\)", item)[0].strip() for item in var_names_with_units]
    variable_mapping = {
        original_col: (
            onset_variables_mapping[var]
            if var in onset_variables_mapping
            else var.lower().replace(" ", "_")
        )
        for original_col, var in zip(original_columns, var_names)
    }
    ds = ds.rename_vars(variable_mapping)

    # Try to match instrument type based on variables available (this information is unfortnately not available withint the CSV)
    vars_of_interest = set(
        var for var in ds if var not in ignored_variables or var.startswith("unnamed")
    )
    if vars_of_interest == {"temperature", "light_intensity"}:
        ds.attrs["instrument_type"] = "Pendant"
    elif vars_of_interest == {"specific_conductance", "temperature", "low_range"}:
        ds.attrs["instrument_type"] = "CT"
    elif vars_of_interest == {"temperature", "specific_conductance"}:
        ds.attrs["instrument_type"] = "CT"
    elif vars_of_interest == {"temperature"}:
        ds.attrs["instrument_type"] = "Tidbit"
    elif vars_of_interest == {"temperature", "pressure", "sensor_depth"}:
        ds.attrs["instrument_type"] = "PT"
    elif vars_of_interest == {
        "temperature",
        "barometric_pressure",
        "pressure",
        "sensor_depth",
    }:
        ds.attrs["instrument_type"] = "WL"
    elif vars_of_interest == {
        "temperature",
        "barometric_pressure",
        "pressure",
        "water_level",
    }:
        ds.attrs["instrument_type"] = "WL"
    elif vars_of_interest == {"temperature", "pressure"}:
        ds.attrs["instrument_type"] = "airPT"
    elif vars_of_interest == {"barometric_pressure"}:
        ds.attrs["instrument_type"] = "airP"
    elif vars_of_interest == {"turbidity"}:
        ds.attrs["instrument_type"] = "turbidity"
    else:
        ds.attrs["instrument_type"] = "unknown"
        logger.warning(
            f"Unknown Hobo instrument type with variables: {vars_of_interest}"
        )

    # # Review units and convert SI system
    if (
        convert_units_to_si
        and "temperature" in ds
        and ("C" not in ds["temperature"].attrs["units"])
    ):
        string_comment = f"Convert temperature ({ds['temperature'].attrs['units']}) to degree Celius [(degF-32)/1.8000]"
        logger.warning(string_comment)
        ds["temperature"] = (ds["temperature"] - 32.0) / 1.8000
        ds["temperature"].attrs["units"] = "degC"
        ds.attrs["history"] += f"{datetime.now()} {string_comment}"
    if (
        convert_units_to_si
        and "conductivity" in ds
        and "uS/cm" not in ds["conductivity"].attrs["units"]
    ):
        logger.warning(
            f"Unknown conductivity units ({ds['conductivity'].attrs['units']})"
        )

    # Output data
    if output == "xarray":
        return ds
    elif "dataframe":
        df = ds.to_dataframe()
        # Include instrument information within the dataframe
        df["instrument_manufacturer"] = ds.attrs["instrument_manufacturer"]
        df["instrument_type"] = ds.attrs["instrument_type"]
        df["instrument_sn"] = ds.attrs["instrument_sn"]
        return df
