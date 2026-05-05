# MMYZ2026
Supporting code, data and figures for Millangoda and Zheng 2026 - 'Sea breeze-triggered storms on the Texas Gulf Coast: propagation, synoptic controls, and urban influences'

If you find any errors in the code or have questions, please contact Malinda Millangoda

# Organization of repository
- data
- notebooks
- figures

# Data

Data analzed in this paper are publicly available from the following sources:
- Multi Radar Multi Sensor precipitation data: Available from the [NOAA MRMS archive](https://registry.opendata.aws/noaa-mrms-pds/) hosted on the AWS Open Data Registry.
- CPC Morphing Technique precipitation data: Available from [NOAA National Centers for Environmental Information Climate Data Record](https://www.ncei.noaa.gov/products/climate-data-records/precipitation-cmorph) archive.
- ERA5 reanalysis data available from the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/datasets)
- Galveston wind observations obtain from Texas Commission on Environmental Quality monitoring stations through [TCEQ Data Portal](https://www.tceq.texas.gov/agency/data)

Due to the large size of raw data, pre-processed data are avaialble in the **Data** directory. The following section will cover detilas on data preporcess to recreate the analysis. 
See **Notebooks** directory for more detail on visulaization.

# Analysis of MRMS Data

The follwoing bash scripts in the **Scripts** directory was used to download the MRMS data.

