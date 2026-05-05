import xarray as xr

# Define cluster categories
clusters = [0, 1, 2, 3]

for cluster in clusters:
    # Load the previously saved files for U and V winds
    daily_mean_u_cluster = xr.open_dataset(f'daily_mean_u_1998_2024_cluster_{cluster}.nc')
    daily_mean_v_cluster = xr.open_dataset(f'daily_mean_v_1998_2024_cluster_{cluster}.nc')
    anomaly_u_cluster = xr.open_dataset(f'anomaly_u_1998_2024_cluster_{cluster}.nc')
    anomaly_v_cluster = xr.open_dataset(f'anomaly_v_1998_2024_cluster_{cluster}.nc')

    # Compute the composite (mean over time)
    composite_mean_u = daily_mean_u_cluster.mean(dim='time')
    composite_mean_v = daily_mean_v_cluster.mean(dim='time')
    composite_anomaly_u = anomaly_u_cluster.mean(dim='time')
    composite_anomaly_v = anomaly_v_cluster.mean(dim='time')

    # Save as NetCDF
    composite_mean_u.to_netcdf(f'composite_mean_u_1998_2024_cluster_{cluster}.nc')
    composite_mean_v.to_netcdf(f'composite_mean_v_1998_2024_cluster_{cluster}.nc')
    composite_anomaly_u.to_netcdf(f'composite_anomaly_u_1998_2024_cluster_{cluster}.nc')
    composite_anomaly_v.to_netcdf(f'composite_anomaly_v_1998_2024_cluster_{cluster}.nc')

    # Print confirmation
    print(f"Saved: composite_mean_u_2021_2024_cluster_{cluster}.nc, composite_mean_v_2021_2024_cluster_{cluster}.nc, composite_anomaly_u_2021_2024_cluster_{cluster}.nc, composite_anomaly_v_2021_2024_cluster_{cluster}.nc")
    print(f"Composite Mean U Cluster {cluster}:", composite_mean_u)
    print(f"Composite Mean V Cluster {cluster}:", composite_mean_v)
    print(f"Composite Anomaly U Cluster {cluster}:", composite_anomaly_u)
    print(f"Composite Anomaly V Cluster {cluster}:", composite_anomaly_v)
