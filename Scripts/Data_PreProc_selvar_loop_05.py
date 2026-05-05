import xarray as xr
import subprocess
from pathlib import Path

# Define latitude and longitude bounds
lat_min, lat_max = 27, 32
lon_min, lon_max = 262, 267

# Directory to save subset NetCDF and GRIB2 files
subset_dir = Path('Subset')
subset_dir.mkdir(exist_ok=True)

# Function to subset and save a GRIB2 file as NetCDF
def subset_and_selvar(input_file):
    # Open GRIB2 file with xarray
    ds = xr.open_dataset(input_file, engine='cfgrib')
    
    # Subset the dataset
    ds_subset = ds.sel(latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max))
    
    # Save subset data to NetCDF
    subset_nc_file = subset_dir / f"{Path(input_file).stem}_HGX.nc"
    ds_subset.to_netcdf(subset_nc_file)
    
    # Select variable using CDO
    subset_selvar_file = subset_dir / f"{Path(input_file).stem}_HGX_selvar.nc"
    subprocess.run(['cdo', 'selvar,unknown', str(subset_nc_file), str(subset_selvar_file)], check=True)
    
    return subset_selvar_file

# Loop through days 1 to 30 for June
for day in range(1, 31):
    day_str = f'{day:02d}'
    date_str = f'202405{day_str}'
    input_file = f'MRMS_RadarOnly_QPE_15M_00.00_{date_str}.grib2'
    
    # Check if the file exists
    if Path(input_file).is_file():
        try:
            subset_file = subset_and_selvar(input_file)
            print(f'Processed and saved subset file: {subset_file}')
        except Exception as e:
            print(f'Error processing file {input_file}: {e}')
    else:
        print(f'File not found: {input_file}')

print(f'Subset files saved to {subset_dir}')
