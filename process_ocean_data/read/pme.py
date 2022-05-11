"""
PME Instruments https://www.pme.com/
"""

import pandas as pd
import re

import warnings


def minidot_txt(path, output="xarray"):
    """
    minidot_txt parses the txt format provided by the PME Minidot instruments.
    """
    # Read MiniDot
    with open(path, "r") as f:
        # Read the headre
        serial_number = f.readline().replace("\n", "")
        metadata = re.search(
            "OS REV: (?P<software_version>\d+\.\d+) Sensor Cal: (?P<instrument_calibration>\d*)",
            f.readline(),
        )

        # If metadata is null than it's likely not a minidot file
        if metadata is None:
            warnings.warn("Failed to read: {path}", RuntimeWarning)
            return pd.DataFrame(), None

        # Read the data with pandas
        ds = pd.read_csv(
            f,
            parse_dates=[0],
            infer_datetime_format=True,
            date_parser=lambda x: pd.to_datetime(x, unit="s", utc=True),
        ).to_xarray()

    ds = ds.rename_vars({var: var.strip() for var in ds})
    ds.attrs = metadata.groupdict()
    ds.attrs.update(
        {
            "instrument_manufacturer": "PME",
            "instrument_model": "MiniDot",
            "instrument_sn": serial_number,
            "history": "",
        }
    )

    if output == "xarray":
        return ds
    elif output == "dataframe":
        df = ds.to_dataframe()
        add_attributes = [
            "instrument_sn",
            "instrument_model",
            "instrument_manufacturer",
        ]
        for att in add_attributes:
            df.insert(0, att, ds.attrs[att])
        return df


def minidot_txts(paths: list or str):
    """
    txts reads individual minidot txt files,
    add the calibration, serial_number and software version
    information as a new column and return a dataframe.
    """
    # If a single string is givien, assume only one path
    if type(paths) is str:
        paths = [paths]

    df = pd.DataFrame()
    for path in paths:
        # Ignore concatenated Cat.TXT files or not TXT file
        if path.endswith("Cat.TXT") or not path.endswith(("TXT", "txt")):
            print(f"Ignore {path}")
            continue

        # Read txt file
        df = df.append(minidot_txt(path))

    return df


def minidot_cat(path):
    """
    cat reads PME MiniDot concatenated CAT files
    """

    with open(path, "r") as f:
        header = f.readline()

        if header != "MiniDOT Logger Concatenated Data File\n":
            raise RuntimeError(
                "Can't recognize the CAT file! \nCAT File should start with ''MiniDOT Logger Concatenated Data File'"
            )
        # Read header and column names and units
        header = [f.readline() for x in range(6)]
        columns = [f.readline() for x in range(2)]

        names = columns[0].replace("\n", "").split(",")
        units = columns[1].replace("\n", "")

        df = pd.read_csv(f, names=names)

    # Extract metadata from header
    metadata = re.search(
        (
            "Sensor:\s*(?P<instrument_sn>.*)\n"
            + "Concatenation Date:\s*(?P<concatenation_date>.*)\n\n"
            + "DO concentration compensated for salinity:\s*(?P<reference_salinity>.*)\n"
            + "Saturation computed at elevation:\s*(?P<elevation>.*)\n"
        ),
        "".join(header),
    ).groupdict()

    return df, metadata
