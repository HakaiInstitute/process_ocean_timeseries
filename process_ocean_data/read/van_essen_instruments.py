import xarray as xr
import pandas as pd
import os
import re

header_end = "[Data]\n"


def MON(file_path):
    """
    Read MON file format from Van Essen Instrument format.
    :param file_path: path to file to read
    :return: metadata dictionary dataframe
    """
    # MON File Header end
    header_end = "[Data]\n"

    with open(file_name) as fid:
        line = ""
        section = "header_info"
        metadata = {}
        metadata[section] = {}
        channel_id = None
        while not line.startswith(header_end):
            # Read line by line
            line = fid.readline()

            if re.match(r"\[.*\]", line):
                section = re.search(r"\[(.*)\]", line)[1].replace(" ", "_")
                if section.startswith("Channel"):
                    channel_id = section.split("_")[1]
                else:
                    channel_id = None

                if channel_id:
                    section = "Channel"

                if section not in metadata:
                    metadata[section] = {}
                if channel_id and channel_id not in metadata[section]:
                    metadata[section][channel_id] = {}

            elif re.match("^=*$", line):
                continue
            elif re.match(r"\s*.*(:|=).*", line):
                key, item = re.split(r"\s*[:=]\s*", line, 1)

                if channel_id and key not in metadata[section][channel_id]:
                    metadata[section][channel_id][key.strip()] = item.rstrip()
                elif channel_id is None:
                    metadata[section][key.strip()] = item.rstrip()
            else:
                print(f"Ignored: {line}")

        channel_names = ["time"] + [
            attrs["Identification"] for id, attrs in metadata["Channel"].items()
        ]
        # Read the rest with pandas
        # Find first how many records exist
        metadata["n_records"] = int(fid.readline())

        # Read data
        df = pd.read_csv(fid, names=channel_names, header=None, sep="\s\s+")

        # If there's less data then expected send a warning
        if len(df) < metadata["n_records"]:
            assert RuntimeWarning(
                f'Missing data, expected {metadata["n_records"]} and found only {len(df)}'
            )
        else:
            # Crop the end if there's extra, should be just the last line that says the end.
            df = df.iloc[: metadata["n_records"]]

    return df, metadata
