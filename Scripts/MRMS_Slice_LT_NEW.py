import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import os

# Define the start and end dates
start_date = datetime(2024, 5, 1)
end_date = datetime(2024, 9, 30)

# Define the output directory
output_dir = './MRMS_data_local_time'

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Loop through each day from 2022-06-01 to 2022-09-30
current_date = start_date
while current_date <= end_date:
    try:
        # Format the date for the file naming convention
        date_str = current_date.strftime('%Y%m%d')

        # Load the netCDF files for the current day and the next day
        file1 = xr.open_dataset(f'MRMS_RadarOnly_QPE_15M_00.00_{date_str}_HGX_selvar.nc')
        next_day_str = (current_date + timedelta(days=1)).strftime('%Y%m%d')
        file2 = xr.open_dataset(f'MRMS_RadarOnly_QPE_15M_00.00_{next_day_str}_HGX_selvar.nc')

        # Combine the datasets along the time dimension
        ds_combined = xr.concat([file1, file2], dim='time')

        # Convert the time coordinate to local time (UTC-5)
        ds_combined['time'] = ds_combined['time'] - pd.Timedelta(hours=5)

        # Define the local time range for the current day
        start_time = pd.Timestamp(f'{current_date.strftime("%Y-%m-%d")} 00:00:00')
        end_time = pd.Timestamp(f'{current_date.strftime("%Y-%m-%d")} 23:45:00')

        # Slice the dataset to get the desired time range for the current day
        ds_sliced = ds_combined.sel(time=slice(start_time, end_time))

        # Save the result to a new netCDF file in the specified output directory
        output_file = os.path.join(output_dir, f'MRMS_RadarOnly_QPE_15M_{date_str}_HGX_selvar_LT.nc')
        ds_sliced.to_netcdf(output_file)

        # Close the datasets
        file1.close()
        file2.close()

        print(f"Processed and saved: {output_file}")

    except FileNotFoundError as e:
        print(f"File not found for {current_date.strftime('%Y-%m-%d')}: {e}")
    
    except Exception as e:
        print(f"Error processing {current_date.strftime('%Y-%m-%d')}: {e}")

    # Move to the next day
    current_date += timedelta(days=1)

print("Processing completed from 2022-06-01 to 2022-09-30.")
