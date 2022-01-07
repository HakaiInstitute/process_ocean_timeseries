import xarray as xr
import pandas as pd
import os
import re

header_end = "[Data]\n"


def MON(file_path, encoding='UTF-8', errors='ignore'):
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
        metadata = {}
        metadata[section] = {}
        channel_id = None
        while not line.startswith(header_end):
            # Read line by line
            line = fid.readline()
            if re.match('\[.+\]',line):
                section = re.search('\[(.+)\]',line)[1]
                if section not in metadata:
                    metadata[section] = {}
            elif re.match('[\w\.\s]+\:\.*',line):
                info = re.search('(?P<key>[\w\s\.]+)\:\s(?P<value>.+)\n',line)
                metadata[section][info['key'].strip()] = info['value'].strip()
            elif re.match('\s*[\w\s]+\s+\=.*',line):
                info = re.search('\s*(?P<key>[\w\s]+)\s+\=(?P<value>.+)',line)
                metadata[section][info['key'].strip()] = info['value'].strip()
            else:
                continue
            
        # Regroup channels 
        metadata['Channel'] = {}
        for key,items in metadata.items():
            if key.startswith('Channel') and key.endswith('from data header'):
                id = re.search('Channel (\d+) from data header',key)[1]
                metadata['Channel'][int(id)] = items

        # Define column names
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
    
    # Remove last line
    if df.iloc[-1]['time']=='END OF DATA FILE OF DATALOGGER FOR WINDOWS':
        # Crop the end
        df = df.iloc[: metadata["n_records"]]
    
    # Convert time variable to UTC
    timezone = re.search('UTC([\-\+]*\d+)',metadata['Series settings']['Instrument number'])[1]+':00'
    df['time'] += ' ' + timezone
    df['time'] = pd.to_datetime(df['time'])

    df = df.rename(columns={
        '1: CONDUCTIVITY':'CONDUCTIVITY',
        '2: SPEC.COND.':'SPEC.COND.'
        }
    )

    # Add Conductivity if missing
    if 'CONDUCTIVITY' not in df.columns and 'SPEC.COND.' in df.columns:
        df['CONDUCTIVITY'] = specific_conductivity_to_conductivity(
            df['SPEC.COND.'], 
            df['TEMPERATURE']
            )

    # Specific Conductance if missing
    if 'CONDUCTIVITY' in df.columns and 'SPEC.COND.' not in df.columns:
        df['SPEC.COND.'] = conductivity_to_specific_conductivity(
            df['CONDUCTIVITY'], 
            df['TEMPERATURE']
            )

    return df, metadata


def specific_conductivity_to_conductivity(
        spec_cond,
        temp,
        theta=1.91 / 100,
        temp_ref=25
):
    return (100+theta*(temp-temp_ref))/100*spec_cond


def conductivity_to_specific_conductivity(
        cond,
        temp,
        theta=1.91 / 100,
        temp_ref=25
):
    return 100/(100+theta*(temp-temp_ref))*cond

