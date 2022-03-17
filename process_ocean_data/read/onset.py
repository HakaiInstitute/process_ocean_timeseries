import pandas as pd
import re

import logging

logger = logging.getLogger(__name__)
onset_variables_mapping = {
    "#": "index",
    "Date Time": "time",
    "Temp": "temperature",
    "Intensity": "light_intensity",
    "EOF": "End Of File",
}


def tidbit_csv(path):

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
        "instrument_type": "Tidbit",
        "instrument_model": "Tidbit",
    }
    # Parse header lines
    timezone = re.search("GMT\s*([\-\+\d\:]*)", df.filter(like="Date Time").columns[0])
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
    if csv_format == "Plot Title":
        plot_title = re.search("Plot Title\: (\w*)\,+", first_line)
        if plot_title:
            df.columns = [col.replace(plot_title[1], "").strip() for col in df.columns]

    columns_info = [
        re.search(
            "^(?P<name>[^\,\(]*)(?:\,(?P<units>[^\(]*)){0,1}(?P<ins>.*){0,1}$", column,
        )
        for column in df.columns
    ]
    df.columns = [col["name"] for col in columns_info]

    # Rename variables available
    df = df.rename(
        columns={
            key: value
            for key, value in onset_variables_mapping.items()
            if key in df.columns
        }
    )

    # Add Variable Columns info
    metadata["variables"] = {col["name"]: col.groupdict() for col in columns_info}

    # Review units
    if "Temp" in metadata["variables"] and (
        "C" not in metadata["variables"]["Temp"]["units"]
        and "(*C)" not in metadata["variables"]["Temp"]["ins"]
    ):
        logger.warning(
            f"Temperature is not in degre Celsius: {metadata['variables']['Temp']}"
        )
        df["temperature"] = (df["temperature"] - 32.0) / 1.8000
        metadata["variables"]["Temp"]["units"] = "degC"
        logger.warning("Temperature was coverted to degree Celius [(degF-32)/1.8000]")

    # Add instrument information to data table
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
        logger.warning('Unknown timezone, we will assume UTC')
        df["time"] = pd.to_datetime(df["time"], utc=True)

    return df, metadata
