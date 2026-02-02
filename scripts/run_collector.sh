#!/bin/bash

# Start WebSocket collector for Polymarket orderbook data
# Runs in background with automatic restart on failure

LOG_DIR="/home/openclaw/.openclaw/workspace/openclawAlpha/logs"
PID_FILE="$LOG_DIR/collector.pid"

mkdir -p "$LOG_DIR"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Collector already running (PID: $OLD_PID)"
        exit 0
    fi
fi

# Start collector
cd /home/openclaw/.openclaw/workspace/openclawAlpha
python3 -u src/websocket_collector.py >> "$LOG_DIR/collector.log" 2>&1 &

NEW_PID=$!
echo $NEW_PID > "$PID_FILE"
echo "Started WebSocket collector (PID: $NEW_PID)"
echo "Logs: $LOG_DIR/collector.log"
