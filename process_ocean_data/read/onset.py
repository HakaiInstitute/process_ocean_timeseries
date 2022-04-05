import pandas as pd
import re
from datetime import datetime

import logging

logger = logging.getLogger(__name__)
onset_variables_mapping = {
    "#": "index",
    "Date Time": "time",
    "Temp": "temperature",
    "Intensity": "light_intensity",
    "Specific Conductance": "specific_conductance",
    "Low Range": "conductivity",
    "EOF": "end_of_file",
    "End of File": "end_of_file":
    "Abs Pres Barom.": "absolute_barometric_pressure",
    "Abs Pres": "absolute_pressure",
    "Sensor Depth": "instrument_depth",
    "Turbidity": "turbidity",
    "Water Level": "water_level",
}


def csv(
    path,
    output="xarray",
    timezone=None,
    convert_units_to_si=True,
    add_instrument_metadata_as_variable=True,
    pd_read_csv_kwargs={},
):

    """tidbit_csv parses the Onset Tidbit CSV format into a pandas dataframe

    Returns:
        df: data in pandas dataframe
        metadata: metadata dictionary
    """
    csv_format = "Plot Title"
    with open(path, "r") as f:
        first_line = f.readline().replace("\n", "")
        if "Serial Number:" in first_line:
            # skip second empty line
            csv_format = "Serial Number"
            f.readline()
        ds = pd.read_csv(f, na_values=[" "], **pd_read_csv_kwargs).to_xarray()

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
                "logger_sn": set(re.findall("LGR S\/N\: (\d*)", columns)),
                "instrument_sn": set(re.findall("SEN S\/N\: (\d*)", columns)),
                "lbl": set(re.findall("lbl: (\d*)", columns)),
            }
        )
    elif csv_format == "Serial Number":
        ds.attrs.update(
            {"instrument_sn": set(re.findall("Serial Number\:(\d+)", first_line))}
        )

    # Rename variables
    original_columns = [var for var in ds]

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
    var_names = [re.split("\,|\(|\)", item)[0].strip() for item in var_names_with_units]
    ds = ds.rename(dict(zip(original_columns, var_names)))

    # Add units to the appropriate field
    for var, units in dict(zip(var_names, units)):
        if units and "Date Time" not in var:
            ds[var].attrs["units"] = units

    # Rename variables available
    df = df.rename(
        columns={
            key: value
            for key, value in onset_variables_mapping.items()
            if key in df.columns
        }
    )
    # Try to match instrument type based on variables available
    ignored_variables = [
        "index",
        "time",
        "Button Up",
        "Button Down",
        "Host Connected",
        "End Of File",
        "Coupler Detached",
        "Coupler Attached",
        "Stopped",
        "Started",
        "Good Battery",
        "Bad Battery",
        "Host Connect",
        "Batt",
        "Low Power",
        "Water Detect",
        "Record",
        "",
    ]
    vars_of_interest = set(var for var in df.columns if var not in ignored_variables)
    if vars_of_interest == {"temperature", "light_intensity"}:
        metadata["instrument_model"] = "Pendant"
    elif vars_of_interest == {"specific_conductance", "temperature", "conductivity"}:
        metadata["instrument_model"] = "CT"
    elif vars_of_interest == {"temperature", "specific_conductance"}:
        metadata["instrument_model"] = "CT"
    elif vars_of_interest == {"temperature"}:
        metadata["instrument_model"] = "Tidbit"
    elif vars_of_interest == {"temperature", "depth"}:
        metadata["instrument_model"] = "PT"
    elif vars_of_interest == {
        "temperature",
        "absolute_barometric_pressure",
        "absolute_pressure",
        "depth",
    }:
        metadata["instrument_model"] = "WL"
    elif vars_of_interest == {
        "temperature",
        "absolute_barometric_pressure",
        "absolute_pressure",
        "water_level",
    }:
        metadata["instrument_model"] = "WL"
    elif vars_of_interest == {"temperature", "absolute_pressure"}:
        metadata["instrument_model"] = "airPT"
    elif vars_of_interest == {"absolute_barometric_pressure"}:
        metadata["instrument_model"] = "airP"
    else:
        metadata["instrument_model"] = "unknown"
        logger.warning(
            f"Unknown Hobo instrument type with variables: {vars_of_interest}"
        )
    # Review units
    if "Temp" in metadata["variables"] and (
        "C" not in metadata["variables"]["Temp"]["units"]
    ):
        logger.warning(
            f"Temperature is not in degre Celsius: {metadata['variables']['Temp']}"
        )
        df["temperature"] = (df["temperature"] - 32.0) / 1.8000
        metadata["variables"]["Temp"]["units"] = "degC"
        logger.warning("Temperature was coverted to degree Celius [(degF-32)/1.8000]")

    # Add instrument information to data table3
    if add_instrument_metadata_as_variable:
        ds["instrument_manufacturer"] = ds.attrs["instrument_manufacturer"]
        ds["instrument_model"] = ds.attrs["instrument_model"]
        ds["instrument_sn"] = ds.attrs["instrument_sn"]

    # Add timezone to time variable
    if timezone:
        ds["time"].values = pd.to_datetime(ds["time"] + " " + timezone[1], utc=True)
    else:
        logger.warning("Unknown timezone, we will assume UTC")
        ds["time"] = pd.to_datetime(ds["time"], utc=True)

    # Output data
    if output == "xarray":
        return ds
    elif "dataframe":
        df = ds.to_dataframe()
        # Include instrument information within the dataframe
        df["instrument_manufacturer"] = ds.attrs["instrument_manufacturer"]
        df["instrument_model"] = ds.attrs["instrument_model"]
        df["instrument_sn"] = ds.attrs["instrument_sn"]
        return df
