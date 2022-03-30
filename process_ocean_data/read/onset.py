import pandas as pd
import re

import logging

logger = logging.getLogger(__name__)
onset_variables_mapping = {
    "#": "index",
    "Date Time": "time",
    "Temp": "temperature",
    "Intensity": "light_intensity",
    "Specific Conductance": "specific_conductance",
    "Low Range": "conductivity",
    "EOF": "End Of File",
    "Abs Pres Barom.": "absolute_barometric_pressure",
    "Abs Pres": "absolute_pressure",
    "Sensor Depth": "depth",
    "Turbidity": "turbidity",
    "Water Level": "water_level",
}


def csv(path, timezone=None, add_instrument_metadata_as_variable=True):

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
        df = pd.read_csv(f, na_values=[" "])

    metadata = {
        "instrument_manufacturer": "Onset",
    }
    # Parse header lines
    if timezone == None:
        timezone = re.search(
            "GMT\s*([\-\+\d\:]*)", df.filter(like="Date Time").columns[0]
        )

    if csv_format == "Plot Title":
        metadata.update(
            {
                "logger_sn": set(re.findall("LGR S\/N\: (\d*)", ":".join(df.columns))),
                "instrument_sn": set(
                    re.findall("SEN S\/N\: (\d*)", ":".join(df.columns))
                ),
                "lbl": set(re.findall("lbl: (\d*)", ":".join(df.columns))),
            }
        )
    elif csv_format == "Serial Number":
        metadata.update(
            {"instrument_sn": set(re.findall("Serial Number\:(\d+)", first_line))}
        )

    # Rename variables
    original_columns = df.columns

    # Drop those components from the column names
    var_names_with_units = [
        re.sub("\s*\({0,1}(LGR|SEN) S\/N\: .*", "", item) for item in df.columns
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
    df.columns = var_names

    # Append variables information to metadata
    metadata["variables"] = {}
    for id, var in enumerate(var_names):
        metadata["variables"].update({var: {"original_name": original_columns[id]}})
        if units[id]:
            metadata["variables"][var]["units"] = units[id]

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
        df.insert(
            loc=0,
            column="instrument_manufacturer",
            value=metadata["instrument_manufacturer"],
        )
        df.insert(
            loc=1, column="instrument_model", value=metadata["instrument_model"],
        )
        df.insert(
            loc=2, column="instrument_sn", value=",".join(metadata["instrument_sn"]),
        )

    # Add timezone to time variable
    if timezone:
        df["time"] = pd.to_datetime(df["time"] + " " + timezone[1], utc=True)
    else:
        logger.warning("Unknown timezone, we will assume UTC")
        df["time"] = pd.to_datetime(df["time"], utc=True)

    return df, metadata
