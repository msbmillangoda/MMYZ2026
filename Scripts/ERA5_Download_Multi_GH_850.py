import cdsapi
import os
import calendar

# -----------------------------
# Settings
# -----------------------------
DATASET = "reanalysis-era5-pressure-levels"

VARIABLES = ["geopotential"]          # Z (units: m^2 s^-2)
PRESSURE_LEVEL = ["850"]              # 850 hPa
MONTHS = ["05", "06", "07", "08", "09"]  # MJJAS
TIMES = [f"{h:02d}:00" for h in range(24)]
AREA = [50, -120, 10, -30]           # N, W, S, E

YEARS = list(range(1998, 2025))      # 1998-2024 inclusive

# Safer for CDS and avoids invalid dates (e.g., months with 30 days)
CHUNK_BY_MONTH = True

COMMON = {
    "product_type": ["reanalysis"],
    "variable": VARIABLES,
    "pressure_level": PRESSURE_LEVEL,
    "time": TIMES,
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": AREA,
}

OUT_DIR = "ERA5_downloads"
os.makedirs(OUT_DIR, exist_ok=True)

# -----------------------------
# Download
# -----------------------------
c = cdsapi.Client()

for year in YEARS:
    if CHUNK_BY_MONTH:
        for month in MONTHS:
            ndays = calendar.monthrange(int(year), int(month))[1]
            days = [f"{d:02d}" for d in range(1, ndays + 1)]

            request = {
                **COMMON,
                "year": [str(year)],
                "month": [month],
                "day": days,
            }

            out_name = f"ERA5_500hPa_Z_{year}_{month}.nc"
            out_path = os.path.join(OUT_DIR, out_name)

            if os.path.exists(out_path):
                print(f"Skipping {out_name}, already exists.")
                continue

            print(f"Downloading {out_name} ...")
            try:
                c.retrieve(DATASET, request, out_path)
                print(f"Finished {out_name}")
            except Exception as e:
                print(f"Failed {out_name}: {e}")

    else:
        # One file per year (heavier; may fail due to 30/31-day months)
        request = {
            **COMMON,
            "year": [str(year)],
            "month": MONTHS,
            "day": [f"{d:02d}" for d in range(1, 32)],
        }

        out_name = f"ERA5_850hPa_Z_{year}.nc"
        out_path = os.path.join(OUT_DIR, out_name)

        if os.path.exists(out_path):
            print(f"Skipping {out_name}, already exists.")
            continue

        print(f"Downloading {out_name} ...")
        try:
            c.retrieve(DATASET, request, out_path)
            print(f"Finished {out_name}")
        except Exception as e:
            print(f"Failed {out_name}: {e}")
