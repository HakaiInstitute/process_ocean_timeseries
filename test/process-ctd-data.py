from process_ocean_data import process_ctd_timeseries
from process_ocean_data.tools import qc
from os import path
import xarray as xr

dest_dir = r"E:\hakai_CTD"
# Retrieve Hakai Instrument Deployment Log
instrument_log = process_ctd_timeseries.get_hakai_ctd_log(dest_dir=dest_dir)

# Download data
instrument_log = process_ctd_timeseries.download_raw_data(
    instrument_log, dest_dir=dest_dir
)

# Processing on time series
for index, row in instrument_log.iterrows():
    process_ctd_timeseries.process_data(row, dest_dir=dest_dir)

# Manual Review
ds = xr.open_dataset(
    path.join(
        dest_dir,
        "Hakai_Seabird-CTD+DO-SBE37 SMP-ODO-SN21328_Calvert-DFO3_20200211-20200828_L1.nc",
    )
)
df = ds.to_dataframe().reset_index()

for var in df.filter(like="qartod").columns:
    df[var] = df[var].astype(int).astype(str)

# NOT COMPATIBLE WITH GOOGLE COLAB
qc.manual_qc_interface(
    df,
    variable_list=["TEMPS901", "PSALST01", "DOXYZZ01", "CNDCST01"],
    flags={"GOOD": "1", "UNKNOWN": "2", "SUSPECT": "3", "FAIL": "4", "MISSING": "9"},
    review_flag="_qartod_aggregate",
)
