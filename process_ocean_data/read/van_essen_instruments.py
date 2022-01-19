import xarray as xr
import pandas as pd
import os
import re

header_end = "[Data]\n"


def MON(file_path, encoding="UTF-8", errors="ignore"):
    """
    Read MON file format from Van Essen Instrument format.
    :param errors: default ignore
    :param encoding: default UTF-8
    :param file_path: path to file to read
    :return: metadata dictionary dataframe
    """
    # MON File Header end
    header_end = "[Data]\n"

    with open(file_path, encoding=encoding, errors=errors) as fid:
        line = ""
        section = "header_info"
        info = {}
        info[section] = {}

        while not line.startswith(header_end):
            # Read line by line
            line = fid.readline()
            if re.match("\[.+\]", line):
                section = re.search("\[(.+)\]", line)[1]
                if section not in info:
                    info[section] = {}
            elif re.match("\s*(?P<key>[\w\s]+)(\=|\:)(?P<value>.+)", line):
                item = re.search("\s*(?P<key>[\w\s]+)(\=|\:)(?P<value>.+)", line)
                info[section][item["key"].strip()] = item["value"].strip()
            else:
                continue

        # Regroup channels
        info["Channel"] = {}
        for key, items in info.items():
            if key.startswith("Channel") and key.endswith("from data header"):
                id = re.search("Channel (\d+) from data header", key)[1]
                info["Channel"][int(id)] = items

        # Define column names
        channel_names = ["time"] + [
            attrs["Identification"] for id, attrs in info["Channel"].items()
        ]
        # Read the rest with pandas
        # Find first how many records exist
        info["n_records"] = int(fid.readline())

        # Read data (Seperator is minimum 2 spaces)
        df = pd.read_csv(
            fid,
            names=channel_names,
            header=None,
            sep="\s\s+",
            skipfooter=1,
            engine="python",
        )

    # If there's less data then expected send a warning
    if len(df) < info["n_records"]:
        assert RuntimeWarning(
            f'Missing data, expected {info["n_records"]} and found only {len(df)}'
        )

    # Remove last line
    if df.iloc[-1]["time"] == "END OF DATA FILE OF DATALOGGER FOR WINDOWS":
        # Crop the end
        df = df.iloc[: info["n_records"]]

    # Convert time variable to UTC
    timezone = (
        re.search("UTC([\-\+]*\d+)", info["Series settings"]["Instrument number"])[1]
        + ":00"
    )
    df["time"] += " " + timezone
    df["time"] = pd.to_datetime(df["time"], utc=True)

    df = df.rename(
        columns={"1: CONDUCTIVITY": "CONDUCTIVITY", "2: SPEC.COND.": "SPEC.COND."}
    )

    # Add Conductivity if missing
    if "CONDUCTIVITY" not in df.columns and "SPEC.COND." in df.columns:
        df["CONDUCTIVITY"] = specific_conductivity_to_conductivity(
            df["SPEC.COND."], df["TEMPERATURE"]
        )

    # Specific Conductance if missing
    if "CONDUCTIVITY" in df.columns and "SPEC.COND." not in df.columns:
        df["SPEC.COND."] = conductivity_to_specific_conductivity(
            df["CONDUCTIVITY"], df["TEMPERATURE"]
        )

    # Reformat metadata to CF/ACDD standard
    metadata = {
        "instrument_manufacturer": "Van Essen Instruments",
        "instrument_type": info["Logger settings"]["Instrument type"],
        "instrument_sn": info["Logger settings"]["Serial number"],
        "time_coverage_resolution": info["Logger settings"]["Sample period"],
        "original_metadata": info,
    }

    return df, metadata


def specific_conductivity_to_conductivity(
    spec_cond, temp, theta=1.91 / 100, temp_ref=25
):
    return (100 + theta * (temp - temp_ref)) / 100 * spec_cond


def conductivity_to_specific_conductivity(cond, temp, theta=1.91 / 100, temp_ref=25):
    return 100 / (100 + theta * (temp - temp_ref)) * cond
