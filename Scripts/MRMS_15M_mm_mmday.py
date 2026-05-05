import xarray as xr
import pandas as pd
import os

# Input and output directories
input_dir = "/Data/mmillang/DYAMOND/MRMS_Comparison/MRMS_15M/"
output_dir = "/Data/mmillang/DYAMOND/MRMS_Comparison/MRMS_15M/MRMS_15M_mmday/"
os.makedirs(output_dir, exist_ok=True)

# Loop through dates from 2022-06-01 to 2022-09-30
start_date = "2021-05-01"
end_date = "2021-09-30"
date_range = pd.date_range(start=start_date, end=end_date)

for date in date_range:
    # Generate file name based on date
    file_name = f"MRMS_RadarOnly_QPE_15M_{date.strftime('%Y%m%d')}_HGX_selvar_LT_5km.nc"
    input_path = os.path.join(input_dir, file_name)
    output_path = os.path.join(output_dir, file_name)
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        continue
    
    # Open the file with xarray
    ds = xr.open_dataset(input_path)
    
    # Assuming the rainfall variable is named "rainfall"
    rainfall_var = "unknown"  # Change this to the actual variable name
    if rainfall_var in ds.variables:
        # Convert 15-minute rainfall (mm) to mm/day
        ds[rainfall_var] = ds[rainfall_var] * 96
        ds[rainfall_var].attrs["units"] = "mm/day"
    
        # Save the modified dataset
        ds.to_netcdf(output_path)
        print(f"Converted and saved: {output_path}")
    else:
        print(f"Rainfall variable not found in file: {input_path}")
