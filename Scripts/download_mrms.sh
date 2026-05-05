#!/bin/bash

# Define the base URL for the data
base_url="https://noaa-mrms-pds.s3.amazonaws.com/CONUS/RadarOnly_QPE_15M_00.00"

# Define the start and end dates
start_date="2021-05-01"
end_date="2021-09-30"

# Define the output directory to save the downloaded files
output_dir="./MRMS_15M_data_2020"

# Create the output directory if it doesn't exist
mkdir -p $output_dir

# Convert start and end dates to seconds since 1970-01-01 (Unix time)
start_sec=$(date -d "$start_date" +%s)
end_sec=$(date -d "$end_date" +%s)

# Loop through each day in the date range
for (( sec=$start_sec; sec<=$end_sec; sec+=86400 )); do
    # Convert current seconds to the current date
    current_date=$(date -u -d @$sec +"%Y-%m-%d")
    year=$(date -u -d @$sec +"%Y")
    month=$(date -u -d @$sec +"%m")
    day=$(date -u -d @$sec +"%d")

    # Loop through each hour (00 to 23)
    for hour in {00..23}; do
        # Loop through each 15-minute interval (00, 15, 30, 45)
        for minute in 00 15 30 45; do
            # Format the filename and URL
            filename="MRMS_RadarOnly_QPE_15M_00.00_${year}${month}${day}-${hour}${minute}00.grib2.gz"
            file_url="${base_url}/${year}${month}${day}/${filename}"

            # Define the local file path
            local_filepath="${output_dir}/${filename}"

            # Check if the file already exists
            if [ -f "$local_filepath" ]; then
                echo "File already exists: $local_filepath, skipping download."
            else
                # Download the file
                echo "Downloading $file_url ..."
                wget -q "$file_url" -O "$local_filepath"

                # Check if the download was successful
                if [ $? -eq 0 ]; then
                    echo "Downloaded: $filename"
                else
                    echo "Failed to download: $filename"
                fi
            fi
        done
    done
done
