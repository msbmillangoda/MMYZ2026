# MMYZ2026
Supporting code, data and figures for Millangoda and Zheng 2026 - 'Sea breeze-triggered storms on the Texas Gulf Coast: propagation, synoptic controls, and urban influences'

If you find any errors in the code or have questions, please contact Malinda Millangoda

# Organization of repository
- **Data:** contains processed data to plot each figure in this study.
- **Notebooks:** contains notebooks required to plot each figure in this study.
- **Raw_Data:** contains some of the raw data used in this study.
- **Figures:** contains all generated figures in this study.
- **Scripts:** contains scripts used to download, preprocess and plot.
- **Utils:** contains required additional files.

# Data

Data analyzed in this paper are publicly available from the following sources:
- Multi Radar Multi Sensor precipitation data: Available from the [NOAA MRMS archive](https://registry.opendata.aws/noaa-mrms-pds/) hosted on the AWS Open Data Registry.
- CPC Morphing Technique precipitation data: Available from [NOAA National Centers for Environmental Information Climate Data Record](https://www.ncei.noaa.gov/products/climate-data-records/precipitation-cmorph) archive.
- ERA5 reanalysis data available from the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/datasets)
- Galveston wind observations obtain from Texas Commission on Environmental Quality monitoring stations through [TCEQ Data Portal](https://www.tceq.texas.gov/agency/data)

Due to the large size of raw data, pre-processed data are avaialble in the **Data** directory. The following section will cover detilas on data preprocess to recreate the analysis. 
See **Notebooks** directory for more detail on visualization.

Before any of the analysis, a conda environment was created to conduct the analysis and to run tobac. This conda environment specifications are avaialble in the **Utils** directory: spec-file.txt

This file could be used to create the environment that is required to run TOBAC and other python and bash scripts used in this study.

# Analysis of MRMS Data (2021-2024)

The follwoing bash and python scripts in the **Scripts** directory was used to download the MRMS data for each year separately and preporcess them for analysis.
- Download data: **download_mrms.sh**
- Unzip & concatenate: **unzip_and_concatenate.sh**
- Subset & convert to netcdf: **Data_Prepoc_selvr_loop_5.py**
- Covert to Local Time: **MRMS_Slice_LT_NEW.py**
- Convert to mm/day: **MRMS_15M_mm_mmday.py**
- Run tobac object tracking: **TOBAC_MRMS.py**
- Combine feature detection data for 2021-2024: **Combine_All_Features.py**

The feature detection files were clustered into 4 clusters using the following script.
- Split feature detection data into 4 clusters: **Split_Features_Cluster.py**

Then the output csv files from the Split_Features_Cluster.py were used to visulaize some of the initial outputs of the analysis. The feature detection files were clustered into 4 clusters identified using k-means clustering. Details of the k-means clusteirng is provided in the analysis of the TCEQ Data section.

Following scripts saved in the **Scripts** directory was used to output the netcdf files required to plot MRMS storm density and initiation density.
- Storm density netcdf file: **Plot_Anomaly_Features_1HR_NEW_CI_ZS_smooth_rainfallcon_NEW_netcdf.py**
- Storm initiation density netcdf file: **Plot_Anomaly_Initiations_1HR_NEW_CI_ZS_smooth_rainfallcon_NEW_netcdf.py**

MRMS raw rainfall data required to run these scripts are provided in the **Raw_Data** directory (**MRMS_diurnal_composite_hourly_2021_2024.nc**)

The required MRMS output (**filtered_free_cells_YYYY_MM_1km.csv**) to generate the netcdf files were prepared by going through the data preprocessing process in the following notebook in the **Notebooks** directory for each year data.
- **MRMS_Data_Filter.ipynb**

# Analysis of CMORPH Data (1998-2024)

The follwoing bash and python scripts in the **Scripts** directory was used to download the CMORPH data for each year separately and preporcess them for analysis.
- Download data: **Download_CMORPH.sh**
- Unzip & concatenate: **unzip_and_concatenate.sh**
- Preprocess data: **Preprocess_CMORPH.py**
- Covert to Local Time: **Local_Time.py**
- Run tobac object tracking: **TOBAC_CMORPH.py**

The feature detection files were clustered into 4 clusters.
- Split feature detection data into 4 clusters: Cluster_Feature_CMORPH.py

Then the output csv files from the Cluster_Feature_CMORPH.py were used to visulaize some of the initial outputs of the analysis. The feature detection files were clustered into 4 clusters identified using k-means clustering. Details of the k-means clusteirng is provided in the analysis of the TCEQ Data section.

Then these clustered wind data files are used to output netcdf files for all 4 clusters together the cluster pairs ( 0-1 and 2-3 ) using the following python scripts in the **Scripts** directory. Processed output netcdf files (included in **Data** directory) are then used directly to plot CMORPH related figures in this study (follow the Jupyter notebooks in **Notebooks** directory for plotting). Required clustered CMORPH raw rainfall data files are available in **Raw_Data** directory (**CMORPH_ADJ_8km_daily_1998_2024_LT_lonadj_clusterX_composite.nc**).
- all clusters: **bin_and_plot_features_v1_NEW_SMOOTHED_precip_diam_CL0_1_2_3_rawrf.py**
- clusters 0 & 1: **bin_and_plot_features_v1_NEW_SMOOTHED_precip_diam_rawrf_CL0_1.py**
- clusters 2 & 3: **bin_and_plot_features_v1_NEW_SMOOTHED_precip_diam_rawrf_CL2_3.py**

These output netcdf files (available in **Data** direcotry in respective figure folder) could be used plot storm density plots related to CMORPH data for onshore and calm wind cases.

Similarly, the following scripts are used to divide the data into urban and non-urban corridors.
- urban corridor: **bin_and_plot_features_v1_NEW_Urban_precip_diam_rawrf.py**
- non-urban corridor: **bin_and_plot_features_v1_NEW_NonUrban_precip_diam_rawrf.py**

These output netcdf files (available in **Data** direcotry in respective figure folder) could be used plot storm density plots related to CMORPH data for urban and non-urban corridors.


# Analysis of TCEQ Wind data

To identify wind clusters we used k-means clustering and for this we downloaded station wind data of Galveston Station from TCEQ website. The downloaded data was then preprocessed to able to run k-means clustering. The following notebooks under the **Notebooks** directory could be used to preprocess and run k-means clustering.
- Preprocess TCEQ wind data: **Preprocess_TCEQ_Wind_1998_2024.ipynb**
- Run k-means clustering: **K_means_cluster.ibynb**
- Cluster wind data days into separate clusters: **Cluster_TCEQ_Wind.ipynb**

The clustered wind data was then used to plot the Figure A3 and also the clustered_wind_data_1998_2024_k4.csv (available in **Utils** directory), which is an output the k-means clustering process was used to identify the different days for each cluster for MRMS and CMORPH data.

# Analysis of ERA5 data

ERA5 850hPa level wind and Geopotential height data was used in this analysis and the follwing scripts were used to download wind and geopotential height data:
 - download 850hPa level U-V wind data: **ERA5_Download_Multi_UV850.py**
 - download 850hPa level geopotential height data: **ERA5_Download_Multi_GH_850.py**

To preprocess the wind data the following python scripts (available in **Scripts** directory) were run in order for U-V wind data.
- **UV_Preprocess_1.py**
- **UV_Preprocess_2.py**
- **UV_Preprocess_3.py**
- **UV_Preprocess_4.py**

To preprocess the geopotential height data the following python scripts (available in **Scripts** directory) were run in order for U-V wind data.
- **GH_Preprocess_1.py**
- **GH_Preprocess_2.py**
- **GH_Preprocess_3.py**
- **GH_Preprocess_4.py**

Then the processed final output data of wind and geopotential height alongside with the clustered_wind_data_1998_2024_k4.csv data was used to plot the Figure 3.





