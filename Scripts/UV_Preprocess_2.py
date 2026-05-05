import xarray as xr
import numpy as np

# Load the dataset (replace with the correct file path)
dataset = xr.open_dataset('850hPa_UV_1998_2024_local.nc')

# Extract U and V wind components
u_wind = dataset['u']  # Zonal wind (east-west)
v_wind = dataset['v']  # Meridional wind (north-south)

# Check if 'valid_time' has units or is already in datetime format
if 'units' in dataset['valid_time'].attrs:
    # If units exist, use decode_cf_datetime to convert to datetime
    valid_time = xr.coding.times.decode_cf_datetime(dataset['valid_time'].values, units=dataset['valid_time'].attrs['units'])
else:
    # If already in datetime format, directly assign the 'valid_time'
    valid_time = dataset['valid_time']

# Assign the 'valid_time' as the time coordinate
u_wind = u_wind.assign_coords(time=valid_time)
v_wind = v_wind.assign_coords(time=valid_time)

# Calculate the daily mean
daily_mean_u = u_wind.resample(time='1D').mean()
daily_mean_v = v_wind.resample(time='1D').mean()

# Calculate the seasonal mean for May to September (2021-2024)
seasonal_mean_u = daily_mean_u.sel(time=slice('1998-05-01', '2024-08-31')).mean('time')
seasonal_mean_v = daily_mean_v.sel(time=slice('1998-05-01', '2024-08-31')).mean('time')

# Calculate the anomaly for each day (subtract seasonal mean from daily mean)
anomaly_u = daily_mean_u - seasonal_mean_u
anomaly_v = daily_mean_v - seasonal_mean_v

# Save results to NetCDF files
daily_mean_u.to_netcdf('daily_mean_u_wind_1998_2024.nc')
seasonal_mean_u.to_netcdf('seasonal_mean_u_wind_1998_2024.nc')
anomaly_u.to_netcdf('u_wind_anomaly_1998_2024.nc')

daily_mean_v.to_netcdf('daily_mean_v_wind_1998_2024.nc')
seasonal_mean_v.to_netcdf('seasonal_mean_v_wind_1998_2024.nc')
anomaly_v.to_netcdf('v_wind_anomaly_1998_2024.nc')

# Optionally, inspect the results
print(daily_mean_u)
print(seasonal_mean_u)
print(anomaly_u)
print(daily_mean_v)
print(seasonal_mean_v)
print(anomaly_v)
