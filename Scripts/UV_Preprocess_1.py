# -*- coding: utf-8 -*-
import xarray as xr
import pandas as pd
from pathlib import Path

# Years to process
YEARS = range(1998, 2025)

# I/O pattern
IN_PATTERN  = "ERA5_850hPa_UV_{year}.nc"
OUT_PATTERN = "ERA5_850hPa_UV_{year}_local.nc"

# Fixed offset for "Houston local time (UTC-5)" as requested
LOCAL_OFFSET_HOURS = 5

def load_and_shift_time(nc_path: Path, local_offset_hours: int = 5) -> xr.Dataset:
    """Open a NetCDF, find its time coordinate ('valid_time' or 'time'),
    shift from UTC by a fixed offset (hours), and return the updated dataset."""
    ds = xr.open_dataset(nc_path)

    # Choose time coordinate name
    time_name = 'valid_time' if 'valid_time' in ds.coords or 'valid_time' in ds.variables else 'time'
    if time_name not in ds:
        raise KeyError(f"No 'valid_time' or 'time' coordinate found in {nc_path.name}")

    time_coord = ds[time_name]

    # Decode to datetime64[ns]
    if pd.api.types.is_datetime64_any_dtype(time_coord.dtype):
        dt_utc = pd.to_datetime(time_coord.values)
    else:
        # Try CF decoding if units are present
        if 'units' in time_coord.attrs:
            dt_utc = xr.coding.times.decode_cf_datetime(
                time_coord.values, units=time_coord.attrs['units']
            )
        else:
            # Last resort: let xarray try decode_cf
            ds = xr.decode_cf(ds, use_cftime=False)
            time_coord = ds[time_name]
            if not pd.api.types.is_datetime64_any_dtype(time_coord.dtype):
                raise TypeError(
                    f"Could not decode '{time_name}' to datetime from {nc_path.name}."
                )
            dt_utc = pd.to_datetime(time_coord.values)

    # Apply fixed UTC->local shift (UTC-5)
    dt_local = dt_utc - pd.Timedelta(hours=local_offset_hours)

    # Assign back (preserve the original coordinate/dimension names)
    ds = ds.assign_coords({time_name: (time_coord.dims, dt_local)})

    # Annotate what we did
    ds[time_name].attrs["note"] = f"time shifted by {local_offset_hours} hours from UTC (fixed offset)"
    return ds

def main():
    for year in YEARS:
        in_path  = Path(IN_PATTERN.format(year=year))
        out_path = Path(OUT_PATTERN.format(year=year))

        if not in_path.exists():
            print(f"[SKIP] {in_path} not found.")
            continue

        try:
            ds_local = load_and_shift_time(in_path, LOCAL_OFFSET_HOURS)
            # Optional lightweight compression for time coordinate
            encoding = {k: {"zlib": True, "complevel": 1} for k in ds_local.data_vars}
            # Keep coords uncompressed for speed/stability
            ds_local.to_netcdf(out_path, encoding=encoding)
            print(f"[OK]  Wrote {out_path}")
            # Quick verification line
            time_name = 'valid_time' if 'valid_time' in ds_local.coords else 'time'
            print(str(ds_local[time_name].isel({time_name: 0}).values), "-> first timestamp (local)")
        except Exception as e:
            print(f"[ERR] {in_path}: {e}")

if __name__ == "__main__":
    main()
