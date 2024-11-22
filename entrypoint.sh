#!/bin/bash

# entrypoint.sh
# Make the script executable in case it isn't already
chmod +x /app/hashcat.sh

# Start hashcat benchmark in background
nohup /app/hashcat.sh &

# Start Python app in foreground
python /app/app.py