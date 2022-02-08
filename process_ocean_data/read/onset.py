import pandas as pd
import re


def tidbit_csv(path):

    """tidbit_csv parses the Onset Tidbit CSV format into a pandas dataframe

    Returns:
        df: data in pandas dataframe
        metadata: metadata dictionary
    """
    with open(path, "r") as f:
        plot_title = f.readline().replace("\n", "")
        info_line = f.readline().replace("\n", "")
        column_names = [
            re.split(",|\s*\(", col)[0] for col in info_line[1:-1].split('","')
        ]
        df = pd.read_csv(
            f,
            names=column_names,
            usecols=["#", "Date Time", "Temp"],
            dtype={"#": int, "Date Time": str, "Temp": float},
            index_col="#",
            engine="c",
        )

    # Rename the variables
    df = df.rename(columns={"#": "index", "Date Time": "time", "Temp": "temperature"})

    # Parse header lines
    timezone = re.search("Date Time, GMT([\-\+\d\:]*)", info_line)[1]
    logger_serials = re.findall("LGR S\/N\: (\d*)", info_line)
    sensor_serials = re.findall("SEN S\/N\: (\d*)", info_line)
    lbl = re.findall("lbl: (\d*)", info_line)

    # Generate Metadata dictionary
    metadata = {
        "instrument_type": "Tidbit",
        "instrument_manufacturer": "Onset",
        "instrument_model": "Tidbit",
        "instrument_sn": sensor_serials[0],
        "lbl": lbl,
        "plot_title": plot_title,
    }

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
        loc=1, column="instrument_model", value=metadata["instrument_model"],
    )
    df.insert(
        loc=2, column="instrument_sn", value=metadata["instrument_sn"],
    )
    # Add timezone to time variable
    df["time"] = pd.to_datetime(df["time"] + " " + timezone, utc=True)

    return df, metadata
