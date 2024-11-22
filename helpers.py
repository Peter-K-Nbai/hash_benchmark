# gpu_hash/helpers.py
# Helper functions to make the app.py file cleaner

import subprocess
import re
import threading
import time
import logging
import asyncio

# Global variables to store hash rates and times
hash_rates = []
times_ms = []

# Counters for unknown results (if either value is "Unknown")
unknown_count = 0

# Lock to ensure thread-safe access to the lists and counters
results_lock = asyncio.Lock()

HASHCAT_OUT_FILE_PATH = "hashcat.out"

# Get the number of GPUs
def get_gpu_count():
    try:
        # Run `nvidia-smi --list-gpus` to get the list of GPUs
        result = subprocess.run(['nvidia-smi', '--list-gpus'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Count the number of lines in the output, each line represents a GPU
        gpu_count = len(result.stdout.strip().split('\n'))
        return gpu_count
    except subprocess.CalledProcessError:
        # If `nvidia-smi` command fails, assume no GPUs are available
        return 0

# Perform the GPU memory check
def get_gpu_memory():
    try:
        # Run `nvidia-smi` and capture its output
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.total,memory.free', '--format=csv,nounits,noheader'],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        
        # Parse the output
        memory_info = result.stdout.strip().split('\n')
        gpus = []
        for info in memory_info:
            total, free = map(int, re.findall(r'\d+', info))
            gpus.append({'total_memory_MB': total, 'free_memory_MB': free})
        
        return gpus  # Return list of dictionaries with memory info
    except subprocess.CalledProcessError as e:
        print("Error querying GPU memory:", e)
        return None


# Run the hashcat benchmark
async def run_hashcat_benchmark(logger):
    global unknown_count, hash_rates, times_ms  # Declare these as global to modify them
    while True:
        try:
            # Run the Hashcat benchmark command on the ethereum hash
        
            # result = subprocess.run(['hashcat', '-b', '-m', '0'],
            #                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            
            # Parse the output for hash rate and time
            # output = result.stdout
            # logger.error(output)
            with open(HASHCAT_OUT_FILE_PATH) as f:
                output = f.read()

            # Regex to capture the hash rate and time (e.g., "1 H/s (9.71ms)")
            hash_rate_match = re.search(r"Speed\.\#\d+.*?([\d.]+ [kMGT]?H/s)\s+\(([\d.]+ms)\)", output)
            if hash_rate_match:
                # hash_rate = hash_rate_match.group(1)  # The hash rate (e.g., 1 H/s)
                # time_ms = hash_rate_match.group(2)  # The time in ms (e.g., 9.71ms)

                hash_rate = float(re.sub(r'[^\d.]', '', hash_rate_match.group(1)))
                time_ms = float(re.sub(r'[^\d.]', '', hash_rate_match.group(2)))
            else:
                hash_rate = "Unknown"
                time_ms = "Unknown"

            # logger.info(f'hash rate: {hash_rate}, time ms: {time_ms}')
    
        
            # Store the results in separate lists with thread safety
            async with results_lock:
                if hash_rate != "Unknown" and time_ms != "Unknown":
                    hash_rates.append(hash_rate)  # Store only the numerical part of the hash rate
                    times_ms.append(time_ms)  # Store only the numerical part of time in ms
                    # logger.info(hash_rates)
                    # logger.info(times_ms)
                else:
                    # If either value is unknown, consider the result as unknown and increment the counter
                    unknown_count += 1
                
                #return()

        except subprocess.CalledProcessError as e:
            print("Error running Hashcat benchmark:", e.stderr)
            logger.error(e.stderr)
            #return None
        
        await asyncio.sleep(60)



# Function to calculate the average benchmark values
async def calculate_average_benchmark():
    global hash_rates, times_ms  # Declare these as global to use the latest data

    # Calculate the average hash rate and time in ms
    async with results_lock:
        # If no valid results exist, return None for averages
        if not hash_rates or not times_ms:
            return None  # Return None explicitly if no data is available

        avg_hash_rate = sum(hash_rates) / len(hash_rates) if hash_rates else 0
        avg_time_ms = sum(times_ms) / len(times_ms) if times_ms else 0

    return {"average_hash_rate": avg_hash_rate, "average_time_ms": avg_time_ms, "total_tests": len(hash_rates)}

# Function to return the count of unknown results (if either value is unknown)
async def get_unknown_counts():
    global unknown_count  # Access the global variable
    async with results_lock:  # Ensure thread-safe access
        if unknown_count is None:
            return None  # Return None if there are no unknown counts
        return {"unknown_count": unknown_count}
