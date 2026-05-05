# -*- coding: latin-1 -*-
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, Polygon, LineString, box
from shapely.affinity import rotate
from geopy.distance import geodesic
from scipy.ndimage import gaussian_filter
from pathlib import Path
import xarray as xr
import warnings

warnings.filterwarnings("ignore", category=UserWarning)

# =============================================
# Setup Directories and Constants
# =============================================
plot_dir = Path("Plot_Feature_Counts_10km_v1_NEW_Urban_precip_diam_rawrf")
plot_dir.mkdir(exist_ok=True)

# Input CSVs (clusters 2 and 3)
files = [
    "all_initiation_points_cluster_0.csv",
    "all_initiation_points_cluster_1.csv",
    "all_initiation_points_cluster_2.csv",
    "all_initiation_points_cluster_3.csv"
]

# -------------------------------
# Outer domain (black box) and green box (urban strip)
# -------------------------------
black_box = Polygon([
    (-95.1487, 26.2953), (-92.4741, 27.6542),
    (-94.7388, 32.1118), (-97.4134, 30.7530)
])

green_box = Polygon([
    (-95.7, 28.8),
    (-94.7, 29.4),
    (-95.8031, 31.5711),
    (-96.8402, 31.0442)
])

# Urban strip = green box (clipped to black box just to be safe)
urban_region = green_box.intersection(black_box).buffer(0)

# Non-urban strip = black box minus green box
nonurban_region = black_box.difference(green_box).buffer(0)

# Middle line (lon, lat)
middle_line = LineString([(-96.2810, 28.5242), (-93.6064, 29.8830)])

# Binning settings
DIST_BIN_WIDTH_KM = 10  # 10-km bands
BIN_RANGE_MIN = -300
BIN_RANGE_MAX = 300
bin_edges = np.arange(BIN_RANGE_MIN, BIN_RANGE_MAX + DIST_BIN_WIDTH_KM, DIST_BIN_WIDTH_KM)
bin_labels = bin_edges[:-1] + DIST_BIN_WIDTH_KM / 2.0  # midpoints

# Cell area (10x10 km)
CELL_SIZE_M = 10_000
CELL_AREA_KM2 = 100.0

# Time window
START_DATE = "1998-06-01"
END_DATE = "2024-08-31"

# Default smoothing
DEFAULT_SMOOTH_SIGMA = 1.5

# =============================================
# Distance Calculation from Middle Line (mask to URBAN region)
# =============================================
def calculate_distance(lat, lon):
    """
    Signed geodesic distance (km) from (lat, lon) to middle_line.
    Returns NaN if point is outside URBAN region (green box).
    """
    point = Point(lon, lat)
    if not urban_region.contains(point):
        return np.nan

    nearest_point = middle_line.interpolate(middle_line.project(point))
    distance_km = geodesic((lat, lon), (nearest_point.y, nearest_point.x)).km

    p1, p2 = middle_line.coords[0], middle_line.coords[-1]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    px, py = lon - p1[0], lat - p1[1]
    cross = dx * py - dy * px
    return distance_km if cross > 0 else -distance_km

# =============================================
# Rainfall helpers: distance masked to a given region polygon
# (lets us bin CMORPH rainfall separately for URBAN and NON-URBAN strips)
# =============================================
def calculate_distance_in_region(lat, lon, region_poly):
    """
    Signed distance (km) from (lat, lon) to middle_line, masked to region_poly.
    Uses SAME sign convention as calculate_distance() in this script.
    """
    point = Point(lon, lat)
    if not region_poly.contains(point):
        return np.nan

    nearest_point = middle_line.interpolate(middle_line.project(point))
    distance_km = geodesic((lat, lon), (nearest_point.y, nearest_point.x)).km

    p1, p2 = middle_line.coords[0], middle_line.coords[-1]
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    px, py = lon - p1[0], lat - p1[1]
    cross = dx * py - dy * px
    return distance_km if cross > 0 else -distance_km


def bin_rainfall_by_distance_and_hour(rainfall_da, region_poly, bin_edges, bin_labels, smooth_sigma=DEFAULT_SMOOTH_SIGMA):
    """
    Bin rainfall (hour, lat, lon) -> (distance_bin, hour) for a given region polygon.

    Returns:
      hours_rf, raw_binned (dist, hour), smoothed_binned (dist, hour)
    """
    lats = rainfall_da.lat.values
    lons = rainfall_da.lon.values
    hours_rf = rainfall_da.hour.values

    # build distance grid with region mask
    grid_points = [Point(lon, lat) for lat in lats for lon in lons]
    dist_list = [calculate_distance_in_region(pt.y, pt.x, region_poly) for pt in grid_points]
    dist_grid = np.array(dist_list).reshape((len(lats), len(lons)))

    dist_flat = dist_grid.flatten()
    bin_idx = np.digitize(dist_flat, bin_edges) - 1

    n_dist = len(bin_labels)
    n_hour = len(hours_rf)

    raw_binned = np.full((n_dist, n_hour), np.nan, dtype="float64")

    base_good = np.isfinite(dist_flat) & (bin_idx >= 0) & (bin_idx < n_dist)

    for t in range(n_hour):
        rain_flat = rainfall_da.isel(hour=t).values.flatten()
        good = base_good & np.isfinite(rain_flat)
        if not np.any(good):
            continue

        for i in range(n_dist):
            m = good & (bin_idx == i)
            if np.any(m):
                raw_binned[i, t] = np.nanmean(rain_flat[m])

    smoothed_binned = gaussian_filter(raw_binned, sigma=smooth_sigma)
    return hours_rf, raw_binned, smoothed_binned

# =============================================
# Load and Filter Data
# =============================================
df_list = []
for file in files:
    try:
        tmp = pd.read_csv(file)
        df_list.append(tmp)
    except FileNotFoundError:
        continue

if not df_list:
    raise FileNotFoundError("No input CSV files were found. Check your 'files' list and paths.")

df = pd.concat(df_list, ignore_index=True)

# Expect columns: time, latitude, longitude, mean_precip, diameter_km
required_cols = {"time", "latitude", "longitude", "mean_precip", "diameter_km"}
if not required_cols.issubset(df.columns):
    missing = required_cols - set(df.columns)
    raise ValueError(f"Input CSVs must contain columns: {required_cols}. Missing: {missing}")

# GeoDataFrame
df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
df = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

# Time filter
df["time"] = pd.to_datetime(df["time"])
df = df[(df["time"] >= START_DATE) & (df["time"] <= END_DATE)]

# Signed distance; NaN if outside URBAN region
df["distance"] = df.apply(lambda row: calculate_distance(row["latitude"], row["longitude"]), axis=1)
df = df.dropna(subset=["distance"]).copy()

# Hour-of-day
df["hour"] = df["time"].dt.hour

# Distinct days for normalization
n_days = df["time"].dt.date.nunique()
if n_days == 0:
    raise ValueError("No days found in the selected time window.")

# =============================================
# Create 10km x 10km Grid Aligned to Middle Line (clipped to URBAN region)
# =============================================
box_proj = gpd.GeoSeries([urban_region], crs="EPSG:4326").to_crs(epsg=3857)[0]
line_proj = gpd.GeoSeries([middle_line], crs="EPSG:4326").to_crs(epsg=3857)[0]

# Rotation angle of the middle line (degrees)
x0, y0 = line_proj.coords[0]
x1, y1 = line_proj.coords[-1]
angle_deg = np.degrees(np.arctan2((y1 - y0), (x1 - x0)))

# Envelope of the urban region in meters
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
    a, b = line_proj.coords[0], line_proj.coords[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    px, py = p.x - a[0], p.y - a[1]
    cross = dx * py - dy * px
    dist_km = line_proj.distance(p) / 1000.0
    return -dist_km if cross < 0 else dist_km

gdf_grid["distance_bin_km"] = gdf_grid["center"].apply(signed_distance_proj)

# Back to EPSG:4326 for spatial join
gdf_grid = gdf_grid.to_crs(epsg=4326)
gdf_grid = gdf_grid.reset_index().rename(columns={"index": "grid_id"})

# =============================================
# Join Features to Grid and Aggregate with Distance Bins
# =============================================
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
          .agg(
              raw_count=("time", "size"),
              mean_precip=("mean_precip", "mean"),
              diameter_km=("diameter_km", "mean"),
          )
          .reset_index()
)

binned["count_per_day"] = binned["raw_count"] / n_days

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

binned["areal_density_per_km2_day"] = (
    binned["count_per_day"] / (binned["n_cells"] * CELL_AREA_KM2)
).replace([np.inf, -np.inf], np.nan)
binned["areal_density_per_100km2_day"] = binned["areal_density_per_km2_day"] * 100.0
binned["per_cell_rate_per_day"] = (
    binned["count_per_day"] / binned["n_cells"]
).replace([np.inf, -np.inf], np.nan)

csv_path = plot_dir / "Feature_Counts_and_Densities_by_Hour_and_Binned_Distance_GREEN.csv"
binned.to_csv(csv_path, index=False)
print("Saved table:", csv_path)

# =============================================
# Helper: Plot a metric with smoothing
# =============================================
def plot_metric(pivot_df, title, cbar_label, outfile, y_limits=(-10, 200), smooth_sigma=DEFAULT_SMOOTH_SIGMA):
    arr = pivot_df.values
    smoothed = gaussian_filter(arr, sigma=smooth_sigma)

    fig, ax = plt.subplots(figsize=(16, 8))
    levels = np.linspace(0, np.nanmax(smoothed), 20)

    c = ax.contourf(
        pivot_df.columns.values,
        pivot_df.index.values[::-1],
        smoothed[::-1],
        levels=levels, cmap=plt.cm.Reds, extend='both'
    )

    ax.axhline(0, color='black', linestyle='--', linewidth=2)
    ax.plot([12, 16], [0, 80], linestyle='--', linewidth=2, color='green', label='Manual Line')

    cbar = plt.colorbar(c, ax=ax)
    cbar.set_label(cbar_label, fontsize=18)

    ax.set_xlabel("Hour (LST)", fontsize=16)
    ax.set_ylabel("Distance from Coast (km)", fontsize=16)
    ax.set_xticks(np.arange(0, 24, 2))
    ax.set_xticklabels(np.arange(0, 24, 2), fontsize=14)
    ax.set_yticks(np.arange(-100, 201, 20))
    ax.set_yticklabels(np.arange(-100, 201, 20), fontsize=14)
    ax.set_title(title, fontsize=18)
    ax.legend()
    ax.set_ylim(*y_limits)
    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()
    print("Saved figure:", outfile)

# =============================================
# Pivots for plotting + NetCDF export
# =============================================
pivot_count_per_day = (
    binned.pivot(index="distance_bin", columns="hour", values="count_per_day")
    .reindex(index=np.sort(bin_labels))
    .fillna(0.0)
)

pivot_density_100km2 = (
    binned.pivot(index="distance_bin", columns="hour", values="areal_density_per_100km2_day")
    .reindex(index=np.sort(bin_labels))
    .fillna(0.0)
)

pivot_mean_precip = (
    binned.pivot(index="distance_bin", columns="hour", values="mean_precip")
    .reindex(index=np.sort(bin_labels))
)

pivot_diameter_km = (
    binned.pivot(index="distance_bin", columns="hour", values="diameter_km")
    .reindex(index=np.sort(bin_labels))
)

plot_metric(
    pivot_count_per_day,
    title="Smoothed Average Count per Day (Urban: Green Box)",
    cbar_label="Average Count per Day (cells / day)",
    outfile=plot_dir / "Smoothed_Count_per_Day_GREEN.png",
    y_limits=(-10, 200),
    smooth_sigma=DEFAULT_SMOOTH_SIGMA
)

plot_metric(
    pivot_density_100km2,
    title="Smoothed Areal Feature Density (Urban: Green Box)",
    cbar_label="Feature Density (cells / 100 km^2 / day)",
    outfile=plot_dir / "Smoothed_Areal_Density_per_100km2_per_Day_GREEN.png",
    y_limits=(-10, 200),
    smooth_sigma=DEFAULT_SMOOTH_SIGMA
)

# =============================================
# Build RAW rainfall fields (ALL clusters combined) for URBAN and NON-URBAN strips
# using ORIGINAL rainfall composite files
# =============================================
rf0 = xr.open_dataarray("CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_cluster0_composite.nc")
rf1 = xr.open_dataarray("CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_cluster1_composite.nc")
rf2 = xr.open_dataarray("CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_cluster2_composite.nc")
rf3 = xr.open_dataarray("CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_cluster3_composite.nc")

rainfall_all = (rf0 + rf1 + rf2 + rf3) / 4.0

hours_rf, raw_rainfall_urban_binned, raw_rainfall_urban_binned_smoothed = bin_rainfall_by_distance_and_hour(
    rainfall_all, urban_region, bin_edges, bin_labels, smooth_sigma=DEFAULT_SMOOTH_SIGMA
)

_, raw_rainfall_nonurban_binned, raw_rainfall_nonurban_binned_smoothed = bin_rainfall_by_distance_and_hour(
    rainfall_all, nonurban_region, bin_edges, bin_labels, smooth_sigma=DEFAULT_SMOOTH_SIGMA
)

# =============================================
# Save unsmoothed metrics to NetCDF (URBAN strip features) + include URBAN/NON-URBAN rainfall fields
# =============================================
hours = pivot_count_per_day.columns.values
distances = pivot_count_per_day.index.values[::-1]

ds = xr.Dataset(
    {
        "count_per_day": (["distance_km", "hour"], pivot_count_per_day.values[::-1].astype("float32")),
        "areal_density_per_100km2_day": (["distance_km", "hour"], pivot_density_100km2.values[::-1].astype("float32")),
        "mean_precip": (["distance_km", "hour"], pivot_mean_precip.values[::-1].astype("float32")),
        "diameter_km": (["distance_km", "hour"], pivot_diameter_km.values[::-1].astype("float32")),

        # rainfall binned fields (ALL clusters, split into strips)
        "raw_rainfall_urban_binned": (["distance_km", "hour"], raw_rainfall_urban_binned[::-1].astype("float32")),
        "raw_rainfall_nonurban_binned": (["distance_km", "hour"], raw_rainfall_nonurban_binned[::-1].astype("float32")),

        # smoothed rainfall binned fields
        "raw_rainfall_urban_binned_smoothed": (["distance_km", "hour"], raw_rainfall_urban_binned_smoothed[::-1].astype("float32")),
        "raw_rainfall_nonurban_binned_smoothed": (["distance_km", "hour"], raw_rainfall_nonurban_binned_smoothed[::-1].astype("float32")),
    },
    coords={
        "hour": ("hour", hours),
        "distance_km": ("distance_km", distances)
    },
    attrs={
        "title": "Urban feature counts/densities and rainfall (urban vs non-urban strips) by hour and distance",
        "description": (
            "Feature fields computed from features restricted to URBAN strip (green_box). "
            "Rainfall fields computed from CMORPH cluster0-3 composites (equal-weight mean across clusters) "
            "and binned by signed distance within URBAN (green_box) and NON-URBAN (black_box minus green_box)."
        ),
        "cell_area_km2": CELL_AREA_KM2,
        "distance_band_width_km": DIST_BIN_WIDTH_KM,
        "time_window": f"{START_DATE} to {END_DATE}",
        "notes": (
            "Feature fields are UNSMOOTHED in this NetCDF; plots apply Gaussian smoothing for visualization. "
            "Rainfall fields include both UNSMOOTHED and SMOOTHED binned versions."
        )
    }
)

for v in [
    "raw_rainfall_urban_binned",
    "raw_rainfall_nonurban_binned",
    "raw_rainfall_urban_binned_smoothed",
    "raw_rainfall_nonurban_binned_smoothed",
]:
    ds[v].attrs.update({
        "units": "mm/hr",
        "source_files": "CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_cluster[0-3]_composite.nc",
        "cluster_combination": "equal-weight mean across clusters 0-3",
        "distance_definition": "signed distance to middle_line; masked by strip polygon"
    })

netcdf_path = plot_dir / "Counts_and_ArealDensities_GREEN_Strong.nc"
ds.to_netcdf(netcdf_path)
print("Saved NetCDF:", netcdf_path)
