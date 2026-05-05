# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import xarray as xr

from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import nearest_points
from shapely.affinity import rotate
from geopy.distance import geodesic
from scipy.ndimage import gaussian_filter
from pathlib import Path
import glob
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# ============================================================
# Setup (match earlier NetCDF variable naming conventions)
# ============================================================
CLUST_TAG = "INITONLY_2021_2024"   # just a tag for filenames

plot_dir = Path("Plot_AbsDensity_Smoothed_WithRain_InitOnly_NEW_NETCDF")
plot_dir.mkdir(exist_ok=True)

# Output NetCDFs (same pattern as earlier examples)
netcdf_path      = plot_dir / f"Counts_and_ArealDensities_BLACK_{CLUST_TAG}.nc"
netcdf_path_sm   = plot_dir / f"Counts_and_ArealDensities_BLACK_{CLUST_TAG}_Smoothed.nc"

# Output figure
out_png = plot_dir / "Smoothed_AbsDensity_with_RainContours_InitOnly_2021_2024_cells_km2_day.png"

# Geometry
coastline = gpd.read_file("clipped_us_coastline.shp")

black_box = Polygon([
    (-95.1487, 26.2953), (-92.4741, 27.6542),
    (-94.7388, 32.1118), (-97.4134, 30.7530)
])
middle_line = LineString([(-96.2810, 28.5242), (-93.6064, 29.8830)])

# Distance binning (keep 20-km bands unless you want 10-km)
DIST_BIN_WIDTH_KM = 20
BIN_RANGE_MIN = -300
BIN_RANGE_MAX = 300
bin_edges = np.arange(BIN_RANGE_MIN, BIN_RANGE_MAX + DIST_BIN_WIDTH_KM, DIST_BIN_WIDTH_KM)
bin_labels = bin_edges[:-1] + DIST_BIN_WIDTH_KM / 2.0  # midpoints (same idea as earlier)

# 10 km x 10 km rotated grid (same approach as your reference script)
CELL_SIZE_M = 10_000
CELL_AREA_KM2 = 100.0

# Time window
START_DATE = "2021-05-01"
END_DATE   = "2024-09-30"

# Smoothing sigmas (like earlier style)
DEFAULT_SMOOTH_SIGMA = 1.5

# ============================================================
# Signed distance function (same sign logic as your original MRMS script)
# ============================================================
def calculate_distance(lat, lon):
    """
    Signed geodesic distance (km) from (lat, lon) to middle_line.
    Returns NaN if outside BLACK BOX.
    Sign uses coastline-projected cross product (same as your initiation+MRMS script).
    """
    point = Point(lon, lat)
    if not black_box.contains(point):
        return np.nan

    nearest_point = middle_line.interpolate(middle_line.project(point))
    distance_km = geodesic((lat, lon), (nearest_point.y, nearest_point.x)).km

    nearest_coast = nearest_points(point, coastline.geometry.unary_union)[1]
    coast_to_line = middle_line.interpolate(
        middle_line.project(Point(nearest_coast.x, nearest_coast.y))
    )

    line_vec = np.array([
        middle_line.coords[1][0] - middle_line.coords[0][0],
        middle_line.coords[1][1] - middle_line.coords[0][1]
    ])
    point_vec = np.array([lon - coast_to_line.x, lat - coast_to_line.y])
    cross = np.cross(line_vec, point_vec)

    return distance_km if cross > 0 else -distance_km

# ============================================================
# Load & preprocess initiation points (INIT ONLY)
# ============================================================
csv_files = glob.glob("filtered_free_cells_20*.csv")
if len(csv_files) == 0:
    raise FileNotFoundError("No files found matching filtered_free_cells_20*.csv")

gdfs = []
for f in csv_files:
    tmp = pd.read_csv(f)
    tmp["time"] = pd.to_datetime(tmp["time"])
    tmp = tmp.sort_values("time")

    # initiation only
    tmp_init = tmp.groupby("cell", sort=False).first().reset_index()
    tmp_init["geometry"] = tmp_init.apply(lambda r: Point(r["longitude"], r["latitude"]), axis=1)
    gdfs.append(gpd.GeoDataFrame(tmp_init, geometry="geometry", crs="EPSG:4326"))

df = pd.concat(gdfs, ignore_index=True)
df["time"] = pd.to_datetime(df["time"])
df = df[(df["time"] >= START_DATE) & (df["time"] <= END_DATE)].copy()

# signed distance (NaN outside BLACK BOX)
df["distance"] = df.apply(lambda r: calculate_distance(r["latitude"], r["longitude"]), axis=1)
df = df.dropna(subset=["distance"]).copy()

# hour-of-day
df["hour"] = df["time"].dt.hour

# normalization days (robust to missing days)
n_days = df["time"].dt.floor("D").nunique()
if n_days == 0:
    raise ValueError("No days found after filtering; n_days=0.")

# ============================================================
# Build 10x10 km grid aligned with middle_line and clipped to BLACK BOX
# ============================================================
box_proj  = gpd.GeoSeries([black_box], crs="EPSG:4326").to_crs(epsg=3857)[0]
line_proj = gpd.GeoSeries([middle_line], crs="EPSG:4326").to_crs(epsg=3857)[0]

# rotation angle of the line
x0, y0 = line_proj.coords[0]
x1, y1 = line_proj.coords[-1]
angle_deg = np.degrees(np.arctan2((y1 - y0), (x1 - x0)))

xmin, ymin, xmax, ymax = box_proj.bounds

grid_cells = []
x = xmin
while x < xmax:
    y = ymin
    while y < ymax:
        cell = box(x, y, x + CELL_SIZE_M, y + CELL_SIZE_M)
        cell = rotate(cell, angle_deg, origin=line_proj.centroid, use_radians=False)
        if box_proj.intersects(cell):
            grid_cells.append(cell)
        y += CELL_SIZE_M
    x += CELL_SIZE_M

gdf_grid = gpd.GeoDataFrame(geometry=grid_cells, crs="EPSG:3857")
gdf_grid["center"] = gdf_grid.geometry.centroid

def signed_distance_proj(p):
    """Signed distance of projected point to projected line, km."""
    a, b = line_proj.coords[0], line_proj.coords[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    px, py = p.x - a[0], p.y - a[1]
    cross = dx * py - dy * px
    dist_km = line_proj.distance(p) / 1000.0
    return -dist_km if cross < 0 else dist_km

gdf_grid["distance_bin_km"] = gdf_grid["center"].apply(signed_distance_proj)

# back to geographic CRS for sjoin
gdf_grid = gdf_grid.to_crs(epsg=4326).reset_index().rename(columns={"index": "grid_id"})

# ============================================================
# Spatial join and aggregate counts by (hour, distance_bin)
# ============================================================
joined = gpd.sjoin(
    df,
    gdf_grid[["grid_id", "geometry", "distance_bin_km"]],
    how="inner",
    predicate="within"
)

joined["distance_bin"] = pd.cut(
    joined["distance_bin_km"],
    bins=bin_edges,
    labels=bin_labels
).astype(float)

binned = (
    joined.groupby(["hour", "distance_bin"])
          .agg(raw_count=("time", "size"))
          .reset_index()
)

# avg cells/day in that 1-hour bin
binned["count_per_day"] = binned["raw_count"] / n_days

# number of grid cells contributing per distance band
grid_bins = pd.cut(
    gdf_grid["distance_bin_km"],
    bins=bin_edges,
    labels=bin_labels
).astype(float)

cells_per_band = (
    pd.Series(1, index=gdf_grid.index)
      .groupby(grid_bins)
      .sum()
      .rename("n_cells")
      .reset_index()
      .rename(columns={"distance_bin_km": "distance_bin"})
)

binned = binned.merge(cells_per_band, on="distance_bin", how="left")
binned["n_cells"] = binned["n_cells"].fillna(0)

# areal density in EXACT SAME NAMING/UNITS STYLE as your earlier script
binned["areal_density_per_km2_day"] = (
    binned["count_per_day"] / (binned["n_cells"] * CELL_AREA_KM2)
).replace([np.inf, -np.inf], np.nan)

binned["areal_density_per_100km2_day"] = binned["areal_density_per_km2_day"] * 100.0

# ============================================================
# Build pivots (distance_bin x hour) with SAME names as earlier script
# ============================================================
hours = np.arange(24)

pivot_count_per_day = (
    binned.pivot(index="distance_bin", columns="hour", values="count_per_day")
    .reindex(index=np.sort(bin_labels), columns=hours)
    .fillna(0.0)
)

pivot_density_100km2 = (
    binned.pivot(index="distance_bin", columns="hour", values="areal_density_per_100km2_day")
    .reindex(index=np.sort(bin_labels), columns=hours)
    .fillna(0.0)
)

# placeholders to keep EXACT variable names present (same as earlier netcdf schema)
# (You don't have mean_precip/diameter from filtered_free_cells; set to NaN.)
pivot_mean_precip = pd.DataFrame(
    np.nan, index=np.sort(bin_labels), columns=hours
)
pivot_mean_diameter = pd.DataFrame(
    np.nan, index=np.sort(bin_labels), columns=hours
)

# ============================================================
# Rainfall composite (MRMS) binned by signed distance & hour
# ============================================================
rain = xr.open_dataarray("MRMS_diurnal_composite_hourly_2021_2024.nc")

lat_name = "latitude" if "latitude" in rain.coords else ("lat" if "lat" in rain.coords else None)
lon_name = "longitude" if "longitude" in rain.coords else ("lon" if "lon" in rain.coords else None)
if lat_name is None or lon_name is None:
    raise ValueError("Could not find latitude/longitude coords in MRMS diurnal composite.")

rain_lat = rain[lat_name].values
rain_lon = rain[lon_name].values

# signed distance grid for MRMS points
rain_pts = [Point(lon, lat) for lat in rain_lat for lon in rain_lon]
rain_dist = np.array([calculate_distance(p.y, p.x) for p in rain_pts]).reshape((len(rain_lat), len(rain_lon)))

dist_flat = rain_dist.flatten()
bin_idx = np.digitize(dist_flat, bin_edges) - 1

raw_rainfall_binned = np.full((len(bin_labels), 24), np.nan, dtype=float)

for h in range(24):
    rain_flat = rain.isel(time=h).values.flatten()
    for i in range(len(bin_labels)):
        mask = bin_idx == i
        if np.any(mask):
            raw_rainfall_binned[i, h] = np.nanmean(rain_flat[mask])

raw_rainfall_binned = np.nan_to_num(raw_rainfall_binned, nan=0.0)

# ============================================================
# NetCDF export (UNSMOOTHED) with EXACT SAME variable names
# ============================================================
# Match your earlier convention: distance_km is reversed for plotting orientation
distances = pivot_count_per_day.index.values[::-1]  # reversed
vals_count = pivot_count_per_day.values[::-1].astype("float32")
vals_dens  = pivot_density_100km2.values[::-1].astype("float32")
vals_mp    = pivot_mean_precip.values[::-1].astype("float32")
vals_md    = pivot_mean_diameter.values[::-1].astype("float32")
vals_rr    = raw_rainfall_binned[::-1].astype("float32")

ds = xr.Dataset(
    {
        "count_per_day": (["distance_km", "hour"], vals_count),
        "areal_density_per_100km2_day": (["distance_km", "hour"], vals_dens),
        "mean_precip": (["distance_km", "hour"], vals_mp),
        "mean_diameter_km": (["distance_km", "hour"], vals_md),

        # EXACT SAME NAME as earlier examples
        "raw_rainfall_binned": (["distance_km", "hour"], vals_rr),
    },
    coords={
        "hour": ("hour", hours),
        "distance_km": ("distance_km", distances.astype("float32")),
    },
    attrs={
        "title": f"Initiation counts/densities and binned MRMS rainfall by hour and distance (Black Box, {CLUST_TAG})",
        "description": (
            "count_per_day: avg cells/day in a 1-hour bin summed over each distance band; "
            "areal_density_per_100km2_day: cells / (100 km^2·day); "
            "mean_precip and mean_diameter_km: not available from filtered_free_cells inputs (stored as NaN); "
            "raw_rainfall_binned: MRMS diurnal composite binned by signed distance (UNSMOOTHED field used as input for contour smoothing)."
        ),
        "n_days": int(n_days),
        "cell_area_km2": float(CELL_AREA_KM2),
        "distance_band_width_km": float(DIST_BIN_WIDTH_KM),
        "time_window": f"{START_DATE} to {END_DATE}",
        "notes": "Values are UNSMOOTHED. Figures apply Gaussian smoothing for visualization only. Region clipped to BLACK BOX."
    }
)

ds["raw_rainfall_binned"].attrs.update({
    "description": "Binned mean rainfall from MRMS diurnal composite (unsmoothed), used as base for contours.",
    "units": "same_as_input_MRMS_file",
    "gaussian_sigma_used_in_smoothed_file": float(DEFAULT_SMOOTH_SIGMA),
})

ds.to_netcdf(netcdf_path)
print("✅ Saved NetCDF:", netcdf_path)

# ============================================================
# NetCDF export (SMOOTHED) with EXACT SAME variable names as earlier examples
# ============================================================
smoothed_count = gaussian_filter(pivot_count_per_day.values, sigma=DEFAULT_SMOOTH_SIGMA)
smoothed_dens  = gaussian_filter(pivot_density_100km2.values, sigma=DEFAULT_SMOOTH_SIGMA)

# keep mean fields as NaN (but still provide smoothed variables with same names)
smoothed_mean_precip   = gaussian_filter(np.nan_to_num(pivot_mean_precip.values, nan=0.0), sigma=DEFAULT_SMOOTH_SIGMA)
smoothed_mean_diameter = gaussian_filter(np.nan_to_num(pivot_mean_diameter.values, nan=0.0), sigma=DEFAULT_SMOOTH_SIGMA)
smoothed_mean_precip[:] = np.nan
smoothed_mean_diameter[:] = np.nan

raw_rainfall_binned_smoothed = gaussian_filter(raw_rainfall_binned, sigma=DEFAULT_SMOOTH_SIGMA)

ds_smoothed = xr.Dataset(
    {
        "count_per_day_smoothed": (["distance_km", "hour"], smoothed_count[::-1].astype("float32")),
        "areal_density_per_100km2_day_smoothed": (["distance_km", "hour"], smoothed_dens[::-1].astype("float32")),
        "mean_precip_smoothed": (["distance_km", "hour"], smoothed_mean_precip[::-1].astype("float32")),
        "mean_diameter_km_smoothed": (["distance_km", "hour"], smoothed_mean_diameter[::-1].astype("float32")),

        # EXACT SAME NAME as earlier examples
        "raw_rainfall_binned_smoothed": (["distance_km", "hour"], raw_rainfall_binned_smoothed[::-1].astype("float32")),
    },
    coords={
        "hour": ("hour", hours),
        "distance_km": ("distance_km", distances.astype("float32")),
    },
    attrs={
        "title": f"Gaussian-smoothed initiation counts/densities and binned MRMS rainfall by hour and distance (Black Box, {CLUST_TAG})",
        "smoothing": "Gaussian filter applied independently in (distance, hour) space.",
        "gaussian_sigma": float(DEFAULT_SMOOTH_SIGMA),
        "n_days": int(n_days),
        "cell_area_km2": float(CELL_AREA_KM2),
        "distance_band_width_km": float(DIST_BIN_WIDTH_KM),
        "time_window": f"{START_DATE} to {END_DATE}",
        "notes": "These fields are SMOOTHED representations intended for visualization/diagnostics. Region clipped to BLACK BOX."
    }
)

ds_smoothed["raw_rainfall_binned_smoothed"].attrs.update({
    "description": "Gaussian-smoothed binned mean rainfall from MRMS diurnal composite (used for contour overlays).",
    "units": "same_as_input_MRMS_file",
    "gaussian_sigma": float(DEFAULT_SMOOTH_SIGMA),
})

ds_smoothed.to_netcdf(netcdf_path_sm)
print("✅ Saved Smoothed NetCDF:", netcdf_path_sm)

# ============================================================
# Plot (use smoothed NetCDF arrays)
# ============================================================
dist_plot = distances.astype(float)

dens_plot = ds_smoothed["areal_density_per_100km2_day_smoothed"].values  # (dist, hour)
rain_plot = ds_smoothed["raw_rainfall_binned_smoothed"].values          # (dist, hour)

plt.figure(figsize=(16, 10))
cf = plt.contourf(
    hours,
    dist_plot,
    dens_plot,
    levels=np.linspace(0, np.nanmax(dens_plot), 20),
    cmap="Reds",
    extend="both"
)

cs = plt.contour(
    hours,
    dist_plot,
    rain_plot,
    levels=[5.0, 5.5, 6.0, 6.5, 7.0],
    colors="black",
    linewidths=1.5
)
plt.clabel(cs, fmt="%.2f", fontsize=18)

plt.axhline(y=0, linestyle="--", color="black", linewidth=2)
plt.plot([10, 17], [0, 80], linestyle="--", color="green", linewidth=2, label="Manual Line")
plt.axhline(y=73.4, linestyle="--", color="blue", linewidth=2, label="Houston (73.4 km)")

cbar = plt.colorbar(cf)
cbar.set_label("Feature Density (cells / 100 km$^2$ / day)", fontsize=28)
cbar.ax.tick_params(labelsize=20)

plt.xlabel("Hour (LST)", fontsize=28)
plt.ylabel("Distance from Coast (km)", fontsize=28)
plt.xticks(fontsize=24)
plt.yticks(fontsize=24)
plt.title("Smoothed Initiation Density with MRMS Rainfall Contours (2021–2024)", fontsize=22)
plt.xlim(0, 23)
plt.ylim(-50, 200)
plt.legend(fontsize=22, loc="upper left")
plt.tight_layout()
plt.savefig(out_png, dpi=300)
plt.close()

print("✅ Saved plot:", out_png)
