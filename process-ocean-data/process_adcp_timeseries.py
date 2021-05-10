from .tools import google, hakai, process

from pycurrents_ADCP_processing import ADCP_processing_L0, ADCP_processing_L1
import xarray as xr
import pandas as pd
import numpy as np
import glob

# File path
dest_dir = r"/mnt/e/hakai_ADCP/"

# Define Spreadsheet ID
# Hakai ADCP Deployment log
# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1fg8QEdZIE1sSYf4lAM-p12LaiBs4Cli8CVJriwaeAFs'
SAMPLE_RANGE_NAME = 'ADCP Deployments!A:AZ'

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

# Produce a metadata file for each Hakai ADCP Deployment based on the metadata variable mapping show below:
hakai_to_ios_map = {'acknowledgement': 'Hakai Mooring Group',
                    'agency': 'Hakai Institute',
                    'anchor_type': 'Anchor Type',  # Need to add a column describing the deployment type,
                    'anchor_drop_time': 'Deployment Time',
                    'anchor_release_time': 'Retrieval Time',
                    'comment': 'Comments',
                    'country': 'Canada',
                    'country_institute_code': '-99',
                    'cruise_description': '',
                    'cut_lead_ensembles': 0,
                    'cut_trail_ensembles': 0,
                    'deployment_cruise_number': '',
                    'geographic_area': 'Region',
                    'history': 'Magnetic Declination was retrieve for the specific location and deployment time from '
                               'NRCAN website.',
                    'instrument_depth': '-99',
                    'latitude': 'Latitude',
                    'longitude': 'Longitude',
                    'platform': 'Platform',  # not sure what it could relate to within Hakai
                    'project': 'Project',
                    'publisher_email': 'info@hakai.org',
                    'return_cruise_number': '',
                    'scientist': 'Scientist',
                    'deployment_number': '',
                    'water_depth': '-99',
                    'instrumentSubtype': 'Instrument Sub Type',
                    'serialNumber': 'Serial Number',
                    'magnetic_variation': 'Magnetic Declination',
                    'instrument_clock_seconds_utc_offset': 'Instrument_clock_seconds_utc_offset'}

hakai.hakai_log_to_ios_csv(df, hakai_to_ios_map, dest_dir)

# Retrieve Raw ADCP data (*.000)
# Create a dictionary with the output file name as key and link to the data as value
adcp_files = {row['file_name']+'.000': row['Link to Raw Data'] for index, row in df.iterrows()}
hakai.download_on_google_drive(adcp_files, dest_dir)

# Apply pycurrent_ADCP_processing to get:
#  Level 0 NetCDF ( raw data converted to NetCDF)
#  Read Level 0  Data and retrieve following information automatically:
#   + Detect start/end times to update cut_lead_ensembles and cut_trail_ensembles
#   + Retrieve Instrument Depth
raw_file_list = glob.glob(dest_dir + '*.000')
for raw_file in raw_file_list:
    meta_file = raw_file[0:-4] + '_meta.csv'

    # Perform Initial L0 processing on the raw data and export as a netCDF file
    ncname_L0 = ADCP_processing_L0.nc_create_L0(f_adcp=raw_file, f_meta=meta_file, dest_dir=dest_dir)

    # Read Level 0 Data
    ds = xr.open_dataset(ncname_L0)

    # Detect start and end times
    #  CMAGZZ## should have some good data
    cmag_min_acceptable_value = 64
    is_good_data = ((ds['CMAGZZ01'] > cmag_min_acceptable_value).any('distance') &
                    (ds['CMAGZZ02'] > cmag_min_acceptable_value).any('distance') &
                    (ds['CMAGZZ03'] > cmag_min_acceptable_value).any('distance') &
                    (ds['CMAGZZ04'] > cmag_min_acceptable_value).any('distance'))
    start_end_results = process.detect_start_end(ds, 'time', 'PRESPR01', is_good_data,
                                                 figure_path=ncname_L0[0:-3]+'_start_end.png')
    # Close data set
    ds.close()

    # Update metadata to reflect results
    # Read L0 meta and update fields for Level 1 processing
    df_meta_l1 = pd.read_csv(raw_file[0:-4]+'_meta.csv').set_index('Name')

    # Update fields
    df_meta_l1.loc['cut_lead_ensembles', 'Value'] = start_end_results['cut_lead_ensembles']
    df_meta_l1.loc['cut_trail_ensembles', 'Value'] = start_end_results['cut_trail_ensembles']
    df_meta_l1.loc['instrument_depth'] = start_end_results['instrument_depth']

    # Add new fields
    df_meta_l1['pressure_offset_at_deployment'] = start_end_results['pressure_offset_deployment']
    df_meta_l1['pressure_offset_at_retrieval'] = start_end_results['pressure_offset_retrieval']

    # Save metadata to L1 metadata
    meta_l1 = raw_file[0:-4]+'_meta_L1.csv'
    df_meta_l1.to_csv(meta_l1)

    # Process L1 Data
    ncname_L1 = ADCP_processing_L1.nc_create_L1(inFile=raw_file, file_meta=meta_l1, dest_dir=dest_dir)

    # Read Level 1 dataset and extra steps
    ds = xr.open_dataset(ncname_L1)

    # Derive Depth from surface variable
    ds['depth'] = -(ds['distance'] - ds['PPSAADCP'])
    ds['depth'].attrs['units'] = 'm'
    ds['depth'].attrs['standard_name'] = 'depth'

    # Flag Currents values
    current_flag_variables = ['LCEWAP01_QC', 'LCNSAP01_QC', 'LRZAAP01_QC']
    
    # Flag out of water data
    for var in current_flag_variables:
        ds = process.update_flag(ds, var, ds['depth'] < 0, true_flag=5)

    # Flag side lobe region from surface data
    side_lobe_coefficient = np.cos(np.deg2rad(int(ds.attrs['beam_angle'])))
    side_lobe_depth = ds['PPSAADCP'] * side_lobe_coefficient + ds.attrs['cellSize'] / 2
    for var in current_flag_variables:
        ds = process.update_flag(ds, var, (ds['depth'] > 0) & (ds['depth'] <= side_lobe_depth), true_flag=5)

    # Replace None which is not compatible with xarray
    ds.attrs['_FillValue'] = np.nan
    # Save to a new NetCDF File
    ncname_L1_hakai = ncname_L1[0:-3] + '_Hakai.nc'
    ds.to_netcdf(ncname_L1[0:-3] + '_Hakai.nc', mode='w', format='NETCDF4')
    ds.close()
