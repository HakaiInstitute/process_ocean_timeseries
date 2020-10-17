import google
import hakai
import process

import seabird
import xarray as xr
import pandas as pd
import numpy as np
import glob

# File path
#dest_dir = r"/mnt/d/hakai_CTD/"
dest_dir = r"D:\hakai_CTD/"

# Define Spreadsheet ID
# Hakai ADCP Deployment log
# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1lkI250zOMJIQ0Z3802QbJHM-dF-zqNxc16AcwxaYCM8'
SAMPLE_RANGE_NAME = 'CTD_log!A:AN'

# Get Hakai ADCP Log data and convert it to a dataframe
val = google.get_google_sheet(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
df = google.convert_google_sheet_to_dataframe(val)

# Apply transformations to Hakai log
#  - Convert times to datetime objects in UTC
#  - Retrieve instrument time offset from UTC
#  - Convert lat/long to decimal degrees
#  - Compute trilateration if available
#  - Retrieve Magnetic Declination
#  - Generate standard Hakai File Name
df = hakai.transform_hakai_log(df, dest_dir)

# Download CTD data
# Create a dictionary with the output file name as key and link to the data as value
adcp_files = {row['file_name']+'.cnv': row['Link to Raw Data'] for index, row in df.iterrows()}
hakai.download_file(adcp_files, dest_dir)


print('works!')
