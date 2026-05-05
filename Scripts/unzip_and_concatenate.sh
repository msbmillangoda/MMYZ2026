#!/bin/bash

# Define the input directory where the downloaded .grib2.gz files are stored
input_dir="./MRMS_15M_data_2024"

# Define the output directory to save the concatenated daily files
output_dir="./MRMS_15M_data_daily_2024"

# Create the output directory if it doesn't exist
mkdir -p $output_dir

# Define the start and end dates
start_date="2024-05-01"
end_date="2024-09-30"

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

    # Define the output file for the current day
    daily_file="${output_dir}/MRMS_RadarOnly_QPE_15M_00.00_${year}${month}${day}.grib2"
    
    # Check if the daily file already exists
    if [ -f "$daily_file" ]; then
        echo "Daily file already exists: $daily_file, skipping."
        continue
    fi

    echo "Processing files for ${current_date}..."

    # Initialize an empty array to hold the unzipped 15-minute files
    files_15m=()

    # Loop through each 15-minute interval (00:00 to 23:45)
    for hour in {00..23}; do
        for minute in 00 15 30 45; do
            # Format the filename for the 15-minute interval
            filename_15m="MRMS_RadarOnly_QPE_15M_00.00_${year}${month}${day}-${hour}${minute}00.grib2.gz"
            file_gz="${input_dir}/${filename_15m}"

            # Check if the 15-minute file exists
            if [ -f "$file_gz" ]; then
                # Unzip the file and store the unzipped file path in the array
                file_unzipped="${input_dir}/${filename_15m%.gz}"  # Remove the .gz extension
                gunzip -c "$file_gz" > "$file_unzipped"
                files_15m+=("$file_unzipped")
            else
                echo "Missing file: $file_gz"
            fi
        done
    done

    # Concatenate all the 15-minute files for the current day
    if [ ${#files_15m[@]} -gt 0 ]; then
        echo "Concatenating files for ${current_date}..."
        cat "${files_15m[@]}" > "$daily_file"

        # Remove the individual unzipped files after concatenation
        for file_unzipped in "${files_15m[@]}"; do
            rm -f "$file_unzipped"
        done

        echo "Daily file created: $daily_file"
    else
        echo "No files found for ${current_date}, skipping concatenation."
    fi
done
