#!/bin/bash

# Set up interrupt handler
trap 'echo -e "\nBenchmark loop interrupted. Exiting..."; exit' INT

echo "Starting hashcat benchmark loop..."
echo "Results will be saved to hashcat.out"
echo "Press Ctrl+C to stop"

# Counter for iterations
count=1

while true; do
    # Create temporary file
    temp_file=$(mktemp)
    
    # Run hashcat benchmark and store in temporary file
    time hashcat -b -m 0 > "$temp_file" 2>&1
    
    # Replace hashcat.out with new content atomically
    mv "$temp_file" hashcat.out
    
    echo "Completed iteration $count"
    
    # Wait 2 seconds between runs
    sleep 2
    
    ((count++))
done
