import pandas as pd
import re

import logging

logger = logging.getLogger(__name__)


def tidbit_csv(path):

    """tidbit_csv parses the Onset Tidbit CSV format into a pandas dataframe

    Returns:
        df: data in pandas dataframe
        metadata: metadata dictionary
    """
    with open(path, "r") as f:
        plot_title = f.readline().replace("\n", "")
        df = pd.read_csv(f, index_col="#")

    # Parse header lines
    timezone = re.search("GMT([\-\+\d\:]*)", df.columns[0])[1]
    logger_serials = re.findall("LGR S\/N\: (\d*)", ":".join(df.columns))
    sensor_serials = re.findall("SEN S\/N\: (\d*)", ":".join(df.columns))
    lbl = re.findall("lbl: (\d*)", ":".join(df.columns))

    # Rename variables
    columns_info = [
        re.search(
            "^(?P<name>[^\,\(]*)(?:\,(?P<units>[^\(]*)){0,1}(?P<ins>\(.*\)){0,1}$",
            column,
        )
        for column in df.columns
    ]
    df.columns = [col["name"] for col in columns_info]

    df = df.rename(
        columns={
            "#": "index",
            "Date Time": "time",
            "Temp": "temperature",
            "Intensity": "light_intensity",
        }
    )

    # Generate Metadata dictionary
    metadata = {
        "instrument_type": "Tidbit",
        "instrument_manufacturer": "Onset",
        "instrument_model": "Tidbit",
        "instrument_sn": sensor_serials[0],
        "lbl": lbl,
        "plot_title": plot_title,
        "variables": {col["name"]: col.groupdict() for col in columns_info},
    }

    if (
        "Temp" in metadata["variables"]
        and "C" not in metadata["variables"]["Temp"]["units"]
    ):
        logger.warning(
            f"Temperature is not in degre Celsius: {metadata['variables']['Temp']}"
        )

    # Confirm that all the serial numbers are the same
    if (
        len(set(logger_serials)) == 1
        and len(set(sensor_serials)) == 1
        and set(logger_serials) == set(sensor_serials)
    ):
        metadata["instrument_sn"] = sensor_serials[0]

    else:
        # I'm not sure when this can really happpen
        metadata["instrument_sn"] = ",".join(set(logger_serials))
        print(f"Sensor and Logger serials are different not sure what to do!")

    # Add instrument information to data table
    df.insert(
        loc=0,
        column="instrument_manufacturer",
        value=metadata["instrument_manufacturer"],
    )
    df.insert(
        loc=1,
        column="instrument_model",
        value=metadata["instrument_model"],
    )
    df.insert(
        loc=2,
        column="instrument_sn",
        value=metadata["instrument_sn"],
    )
    # Add timezone to time variable
    df["time"] = pd.to_datetime(df["time"] + " " + timezone, utc=True)

    return df, metadata
