# from __future__ import print_function

import datetime as dt
import re
import warnings
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import utm
from pytz import timezone

from . import geo
from . import google


def convert_hakai_datetime(date_str):
    """Simple method to parse the date/time variables available within the Hakai Instrument logs. The tool will convert
    PDT/PST to local time America/Vancouver or UTC if specified."""
    if not date_str:
        return pd.NaT

    # Retrieve timezone
    date_str_tz = re.search("PST|PDT|UTC|GMT", date_str, re.IGNORECASE)
    if date_str_tz:
        date_str = date_str.replace(date_str_tz[0], "")

    date = pd.to_datetime(date_str, errors="coerce")

    # Handle the timezone
    if date_str_tz:
        if date_str_tz[0].upper() in ["PST", "PDT"]:
            date = timezone("America/Vancouver").localize(date)
        elif date_str_tz[0].upper() in ["GMT", "UTC"]:
            date = timezone("UTC").localize(date)
        else:
            raise RuntimeError(
                "Can" "t recognize the timezone: {0}".format(timezone[0])
            )
    else:
        warnings.warn(
            "No timezone information avaiable, we" "ll assume UTC.", UserWarning
        )
        date = timezone("UTC").localize(date)

    return date


def transform_hakai_log(df, dest_dir, print_figure=False, get_mag_dec=False):
    """
    The transform_hakai_log function apply the following transformation to the Hakai Log
    Apply transformations to Hakai log
     - Convert times to datetime objects in UTC
     - Retrieve instrument time offset from UTC
     - Convert lat/long to decimal degrees
     - Compute trilateration if available
     - Generate standard Hakai File Name
    """
    # Convert latitude/longitude string data to decimal
    for col in df.filter(regex="latitude|Latitude|Longitude|longitude").columns:
        if df[col].dtypes == object:
            df[col] = df[col].apply(geo.dms2dd)

    # Convert time columns to datetime objects and Convert PST to local Vancouver time
    df = df.replace({"-": None, "NaT": None, pd.NA: None}).replace(
        {"^\s*$": None}, regex=True
    )
    time_columns = df.filter(regex="Time|Clock").columns

    for col in time_columns:
        df[col] = df[col].apply(convert_hakai_datetime)

    # Retrieve Instrument Time zone from Internal Clock Sync and/or Start Time
    print("Retrieve Time Zone Internal Clock Sync or Start Time")
    for index, row in df.iterrows():
        syncTimeZone = row["Internal Clock Sync Time"].tzinfo
        startTimeZone = row["Start Time"].tzinfo

        if syncTimeZone == startTimeZone:
            df.at[index, "Instrument_clock_seconds_utc_offset"] = (
                row["Internal Clock Sync Time"].utcoffset().total_seconds()
            )

    # Convert all times to UTC
    for col in time_columns:
        try:
            df[col] = df[col].dt.tz_convert(timezone("UTC"))
        except:
            df[col] = pd.to_datetime(df[col], utc=True)

    # Get Magnetic Declination from NRCAN
    if get_mag_dec:
        print("Get Magnetic Declination Values from NRCAN")
        for index, row in df.iterrows():
            start_time = row["Deployment Time"]

            (
                df.at[index, "Magnetic Declination"],
                df.at[index, "Yearly Magnetic Drift"],
            ) = geo.get_mag_dec_from_nrcan(
                start_time,
                row["Instrument Deployment Latitude"],
                row["Instrument Deployment Longitude"],
            )
    # TODO Maybe add something to the history than mentions where come from the magnetic declination

    # Define file name
    # 'Hakai_[Manufacturer]-[Instrumen Type]_[Instrument Model]-SN[Serial Number]_[Hakai Region]-[Station]_[StartDate: yyyymmdd]{opt: _[End Date]}
    for index, row in df.iterrows():
        file_name_out = "Hakai"
        file_name_out += "_{0}-{1}-{2}-SN{3}".format(
            row["Instrument Manufacturer"],
            row["Instrument Type"],
            row["Instrument Sub Type"],
            row["Serial Number"],
        )
        file_name_out += "_{0}-{1}".format(row["Region"], row["Site"])
        file_name_out += row["Deployment Time"].strftime("_%Y%m%d")

        if pd.notnull(row["Retrieval Time"]):
            file_name_out += row["Retrieval Time"].strftime("-%Y%m%d")

        sub_path = row["Region"] + "/" + row["Site"] + "/"

        df.at[index, "sub_path"] = sub_path
        df.at[index, "file_name"] = file_name_out

    # Get trilateration results
    print("Triangulate deployment location")
    for index, dd in df.iterrows():
        if pd.notnull(dd["Latitude:Triangulation1"]):
            lat_loc = []
            lon_loc = []
            site_range = []
            n_station = len(dd.filter(regex="Latitude:Triangulation"))
            for ii in range(n_station):
                if pd.notnull(dd["Latitude:Triangulation" + str(ii + 1)]):
                    lat_loc.append(dd["Latitude:Triangulation" + str(ii + 1)])
                    lon_loc.append(dd["Longitude:Triangulation" + str(ii + 1)])
                    site_range.append(float(dd["Range:Triangulation" + str(ii + 1)]))
            # Convert to UTM coordinates
            utm_loc = utm.from_latlon(np.array(lat_loc), np.array(lon_loc))
            # Apply triangulation
            utm_triang = geo.trilateration_from_utm(
                np.array(site_range),
                np.array(
                    [[utm_loc[0][ii], utm_loc[1][ii]] for ii in range(len(lat_loc))]
                ),
            )
            # Convert back to lat/long coordinates
            ll_triang = utm.to_latlon(
                utm_triang[0], utm_triang[1], utm_loc[2], utm_loc[3]
            )

            # Save to DataFrame the results
            df.at[index, "Latitude:Triangulation_Results"] = ll_triang[0]
            df.at[index, "Longitude:Triangulation_Results"] = ll_triang[1]

            # Make a figure of the result
            if print_figure:
                print("Generate Figure")
                fig, ax = plt.subplots(figsize=[10, 10])
                for pos in range(len(utm_loc[1])):
                    plt.scatter(utm_loc[1][pos], utm_loc[0][pos], color="b")
                    cc = plt.Circle(
                        (utm_loc[1][pos], utm_loc[0][pos]),
                        site_range[pos],
                        alpha=0.1,
                        edgecolor="k",
                    )
                    ax.add_artist(cc)
                plt.scatter(utm_triang[1], utm_triang[0], color="r")
                ax.set_aspect("equal")
                plt.xlabel("East UTM [m]")
                plt.ylabel("North UTM [m]")
                plt.title(dd["file_name"])

                # Output Figure for future reference
                fig.savefig(
                    dest_dir + dd["file_name"] + "_triangulation.png",
                    facecolor="w",
                    format="png",
                )

    # Create a position field which is the triangulation position
    # if available otherwise it would be the deployment location
    df["Latitude"] = df["Latitude:Triangulation_Results"]
    df["Longitude"] = df["Longitude:Triangulation_Results"]

    df["Latitude"].fillna(df["Instrument Deployment Latitude"], inplace=True)
    df["Longitude"].fillna(df["Instrument Deployment Longitude"], inplace=True)
    return df


def hakai_log_to_ios_csv(df, hakai_to_ios_map, dest_dir):
    """
    Map Hakai to IOS metadata variables based on the following
    If a value corresponds to a column in the hakai log,
    the hakai log value for that column will be copied to the pycurrent metadata.
    If the string do not correspond to any columns it will be assumed to be the default value.
    Not sure what to do with the empty values yet. Need testing with pycurrent package!
    """

    # Load a default ios metadata form
    ios_reference_path = os.path.join(
        os.path.dirname(__file__), "ios_adcp_processing_metadata_form.csv"
    )
    df_ios = pd.read_csv(ios_reference_path)

    # Distinguish metadata that needs to be retrieved from the Hakai log, the default value or the empty ones
    # from_hakai_log = {} # TODO remove if not needed
    empty_fields = {
        key: value for key, value in hakai_to_ios_map.items() if value == ""
    }
    from_hakai_log = {
        key: value for key, value in hakai_to_ios_map.items() if value in df.columns
    }
    default_fields = dict(
        set(hakai_to_ios_map.items())
        - set(empty_fields.items())
        - set(from_hakai_log.items())
    )

    print("Empty Fields:")
    print(empty_fields.keys())
    print("From Hakai Log:")
    print(from_hakai_log.keys())
    print("Default Values:")
    print(default_fields)

    # Rename columns in Hakai log to match IOS
    df_hakai_ios = df.rename({v: k for k, v in from_hakai_log.items()}, axis="columns")

    # Combine default and defined values into one csv file for raw ADCP data to be processed
    df_standard = df_ios
    df_standard = df_standard.set_index("Name")
    df_standard["Value"] = None
    df_standard["Value"].update(pd.Series(default_fields))
    df_standard["Value"].update(pd.Series(empty_fields))

    # Go through each deployment and create a CSV file of the metadata
    for index, rows in df_hakai_ios.iterrows():
        df_out = df_standard.copy()
        df_out["Value"].update(rows)

        # Ignore rows with empty values
        df_out = df_out.replace("", np.nan).dropna(subset=["Value"])

        # Convert datetime to "yyyy-mm-dd HH:MM:SS UTC" format
        for index, value in df_out["Value"].iteritems():
            if isinstance(value, dt.date) and pd.notnull(df_out.at[index, "Value"]):
                df_out.at[index, "Value"] = df_out.at[index, "Value"].strftime(
                    "%y-%m-%d %H:%M:%S UTC"
                )

        print(df_out["Value"])
        df_out.to_csv(dest_dir + rows["file_name"] + "_meta.csv")


def download_on_google_drive(file_dict, dest_dir):
    """Method to download a file saved on google drive based on a share link with it.
    The tool will then retrieve the file google id and the download it through the google package."""
    for key, value in file_dict.items():
        if value:
            print("Download " + key)
            google_file_id = re.split("id=|file/d/|/view", value)[1]
            print("Google file_id=" + google_file_id)
            google.get_google_drive_file(google_file_id, dest_dir + key)
            # TODO make to download tool compatible with not just google drive
