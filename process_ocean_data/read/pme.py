"""
PME Instruments https://www.pme.com/
"""

import pandas as pd
import re


def minidot_txt(path):
    """
    minidot_txt parses the txt format provided by the PME Minidot instruments.
    """
    # Read MiniDot
    with open(path,'r') as f:
        # Read the headre
        serial_number = f.readline().replace('\n','')
        metadata =  re.search('OS REV: (?P<version>\d+\.\d+) Sensor Cal: (?P<calibration>\d*)',f.readline())
        
        # Read the data with pandas
        df = pd.read_csv(f)

    metadata['serial_number'] = serial_number

    # Convert time to datetime and include
    df['time'] = pd.to_timedelta(df['Time (sec)'],unit='s') + pd.to_datetime('1970-01-01T00:00:00Z')
    return df, metadata

def merge_minidot_txts(paths):
    """
    merge_minidot_txts reads individual minidot txt files, 
    add the calibration, serial_number and software version 
    information as a new column and return a dataframe.
    """

    df = pd.DataFrame()
    for path in paths:
        # Read txt file
        df_temp, metadata = minidot_txt(path)

        df_temp['software_version'] = metadata['version']
        df_temp['serial_number'] = metadata['serial_number']
        df_temp['calibration'] = metadata['calibration']

        # Add to previous data
        df = df.append(df_temp)
    return df
    