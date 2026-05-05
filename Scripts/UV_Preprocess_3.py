import xarray as xr
import pandas as pd
import numpy as np

# Load the daily mean and anomaly datasets for U and V winds
daily_mean_u = xr.open_dataset('daily_mean_u_wind_1998_2024.nc')
daily_mean_v = xr.open_dataset('daily_mean_v_wind_1998_2024.nc')
anomaly_u = xr.open_dataset('u_wind_anomaly_1998_2024.nc')
anomaly_v = xr.open_dataset('v_wind_anomaly_1998_2024.nc')

# Load the CSV file with cluster information
cluster_df = pd.read_csv('clustered_wind_data_1998_2024_k4.csv')

# Convert the 'date' column to pandas datetime
cluster_df['Date'] = pd.to_datetime(cluster_df['Date'])

# Convert 'time' in NetCDF datasets to pandas datetime
daily_mean_u['time'] = pd.to_datetime(daily_mean_u['time'].values)
daily_mean_v['time'] = pd.to_datetime(daily_mean_v['time'].values)
anomaly_u['time'] = pd.to_datetime(anomaly_u['time'].values)
anomaly_v['time'] = pd.to_datetime(anomaly_v['time'].values)

# Merge the cluster data with NetCDF time data
cluster_df.set_index('Date', inplace=True)

# Extract only the dates that exist in the dataset
valid_dates = cluster_df.index.intersection(daily_mean_u['time'].values)

# Select only matching times in both datasets
daily_mean_u_selected = daily_mean_u.sel(time=valid_dates)
daily_mean_v_selected = daily_mean_v.sel(time=valid_dates)
anomaly_u_selected = anomaly_u.sel(time=valid_dates)
anomaly_v_selected = anomaly_v.sel(time=valid_dates)

# Map the cluster values to the selected datasets
clusters = cluster_df.loc[valid_dates, 'Cluster']

# Iterate over unique clusters (0, 1, 2, 3) and save separate files
for cluster in [0, 1, 2, 3]:
    cluster_dates = clusters[clusters == cluster].index

    # Select only the data corresponding to the current cluster
    daily_mean_u_cluster = daily_mean_u_selected.sel(time=cluster_dates)
    daily_mean_v_cluster = daily_mean_v_selected.sel(time=cluster_dates)
    anomaly_u_cluster = anomaly_u_selected.sel(time=cluster_dates)
    anomaly_v_cluster = anomaly_v_selected.sel(time=cluster_dates)

    # Save as NetCDF
    daily_mean_u_cluster.to_netcdf(f'daily_mean_u_1998_2024_cluster_{cluster}.nc')
    daily_mean_v_cluster.to_netcdf(f'daily_mean_v_1998_2024_cluster_{cluster}.nc')
    anomaly_u_cluster.to_netcdf(f'anomaly_u_1998_2024_cluster_{cluster}.nc')
    anomaly_v_cluster.to_netcdf(f'anomaly_v_1998_2024_cluster_{cluster}.nc')

    # Print to check
    print(f"Saved: daily_mean_u_2021_2024_cluster_{cluster}.nc, daily_mean_v_2021_2024_cluster_{cluster}.nc, anomaly_u_2021_2024_cluster_{cluster}.nc, anomaly_v_2021_2024_cluster_{cluster}.nc")
    print(f"Daily Mean U Cluster {cluster}:", daily_mean_u_cluster)
    print(f"Daily Mean V Cluster {cluster}:", daily_mean_v_cluster)
    print(f"Anomaly U Cluster {cluster}:", anomaly_u_cluster)
    print(f"Anomaly V Cluster {cluster}:", anomaly_v_cluster)
