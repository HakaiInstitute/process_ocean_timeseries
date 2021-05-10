import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr


def detect_start_end(ds, time_variable, pressure_variable,
                     good_data_mask=None,
                     pressure_threshold=3,
                     pressure_difference_threshold=0.3,
                     time_dim='time',
                     plot_results=True,
                     figure_path='detect_deployment_startend.png'):

    # Create mask of good data
    is_good_data = (ds[pressure_variable] > pressure_threshold) & \
                   (abs(ds[pressure_variable].diff(time_dim)) < pressure_difference_threshold) \

    # Is mask input if given
    if good_data_mask is not None:
        is_good_data = is_good_data & good_data_mask

    ds_cropped = ds.where(is_good_data, drop=True)

    first_good_record_time = ds_cropped[time_variable].min()
    last_good_record_time = ds_cropped[time_variable].max()

    cut_lead_ensembles = int((ds[time_variable] < first_good_record_time.values).argmin().values)
    cut_trail_ensembles = len(ds[time_variable]) - int(
        (ds[time_variable] > last_good_record_time.values).argmax().values)

    # Review in air pressure value for offset
    pressure_offset_deployment = xr.where(
        (ds[time_variable] < first_good_record_time), ds[pressure_variable], np.nan).median()

    pressure_offset_retrieval = xr.where(
        (ds[time_variable] > last_good_record_time), ds[pressure_variable], np.nan).median()

    print('Pressure Offset [pre, post] = [' + str(pressure_offset_deployment.values) + ', ' + str(
        pressure_offset_retrieval.values) + ']')

    instrument_depth = ds_cropped[pressure_variable].mean()

    if plot_results:
        # Show resulting values
        fig, axes = plt.subplots(ncols=2)

        ds[pressure_variable].plot(label='RAW', ax=axes[0])
        ds_cropped[pressure_variable].plot(label='GOOD', ax=axes[0])
        axes[0].set_title('Deployment')
        ds[pressure_variable].plot(label='RAW', ax=axes[1])
        ds_cropped[pressure_variable].plot(label='GOOD', ax=axes[1])
        axes[1].set_title('Retrieval')
        axes[1].yaxis.tick_right()
        axes[1].yaxis.set_label_position("right")

        # Try to zoom within 1 hour of deployment and retrieval times if possible
        try:
            time_interval = pd.Timedelta(hours=1)
            axes[0].set_xlim([first_good_record_time.values - time_interval, first_good_record_time.values + time_interval])
            axes[1].set_xlim([last_good_record_time.values - time_interval, last_good_record_time.values + time_interval])
        finally:
            print('Can''t recognize time variable')

        axes[0].legend()
        plt.draw()
        plt.savefig(figure_path, dpi=300)

    return {'first_good_record_time': first_good_record_time, 'last_good_record_time': last_good_record_time,
            'cut_lead_ensembles': cut_lead_ensembles, 'cut_trail_ensembles': cut_trail_ensembles,
            'pressure_offset_deployment': pressure_offset_deployment,
            'pressure_offset_retrieval': pressure_offset_retrieval,
            'instrument_depth': instrument_depth}


def update_flag(ds, var, mask, true_flag=None, false_flag=None, history=''):
    # Keep attributes associated to variable
    temp_var = ds[var]

    if true_flag is None:
        true_flag = ds[var]
    if false_flag is None:
        false_flag = ds[var]

    ds[var] = xr.where(mask, true_flag, false_flag)
    ds[var].attrs = temp_var.attrs

    # Add to history attribute
    # TODO Missing the history attribute contribution
    # Could be at the variable or global level
    return ds
