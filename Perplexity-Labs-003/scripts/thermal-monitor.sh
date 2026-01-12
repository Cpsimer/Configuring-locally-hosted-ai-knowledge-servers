#!/bin/bash
# ~/ai-idp/scripts/thermal-monitor.sh
# Lightweight GPU thermal monitoring for AI IDP
# Version: 1.0 | Date: 2026-01-12
#
# Alternative to enterprise DCGM for single-user deployment
# Monitors GPU temperature, power, utilization with alerting

set -euo pipefail

LOG_DIR="/var/log/ai-idp"
LOG_FILE="${LOG_DIR}/gpu-thermal.csv"
ALERT_LOG="${LOG_DIR}/alerts.log"
ALERT_TEMP=${ALERT_TEMP:-85}      # Warning threshold (Celsius)
THROTTLE_TEMP=${THROTTLE_TEMP:-90} # Critical threshold
SAMPLE_INTERVAL=${SAMPLE_INTERVAL:-30}  # Seconds between samples

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize log with header if new file
if [ ! -f "$LOG_FILE" ]; then
    echo "timestamp,temperature_c,power_w,utilization_pct,memory_used_mb,memory_total_mb,fan_speed_pct" > "$LOG_FILE"
    echo "✓ Created thermal log: $LOG_FILE"
fi

echo "=== GPU Thermal Monitor Started ==="
echo "Alert threshold: ${ALERT_TEMP}°C"
echo "Throttle threshold: ${THROTTLE_TEMP}°C"
echo "Sample interval: ${SAMPLE_INTERVAL}s"
echo "Log file: $LOG_FILE"
echo ""

# Function to send alert (customize as needed)
send_alert() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    
    echo "[$timestamp] [$level] $message" | tee -a "$ALERT_LOG"
    
    # Optional: Desktop notification (if running with display)
    if command -v notify-send &> /dev/null && [ -n "${DISPLAY:-}" ]; then
        notify-send -u critical "GPU Thermal Alert" "$message"
    fi
    
    # Optional: Send to webhook (uncomment and configure)
    # curl -X POST -H "Content-Type: application/json" \
    #     -d "{\"level\":\"$level\",\"message\":\"$message\"}" \
    #     http://localhost:5678/webhook/gpu-alert
}

# Main monitoring loop
while true; do
    # Query GPU metrics
    METRICS=$(nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total,fan.speed \
        --format=csv,noheader,nounits 2>/dev/null || echo "ERROR")
    
    if [ "$METRICS" = "ERROR" ] || [ -z "$METRICS" ]; then
        echo "[$(date -Iseconds)] ERROR: nvidia-smi query failed" | tee -a "$ALERT_LOG"
        sleep "$SAMPLE_INTERVAL"
        continue
    fi
    
    # Parse temperature
    TEMP=$(echo "$METRICS" | cut -d',' -f1 | tr -d ' ')
    POWER=$(echo "$METRICS" | cut -d',' -f2 | tr -d ' ')
    UTIL=$(echo "$METRICS" | cut -d',' -f3 | tr -d ' ')
    MEM_USED=$(echo "$METRICS" | cut -d',' -f4 | tr -d ' ')
    MEM_TOTAL=$(echo "$METRICS" | cut -d',' -f5 | tr -d ' ')
    FAN=$(echo "$METRICS" | cut -d',' -f6 | tr -d ' ')
    
    TIMESTAMP=$(date -Iseconds)
    
    # Log metrics
    echo "$TIMESTAMP,$TEMP,$POWER,$UTIL,$MEM_USED,$MEM_TOTAL,$FAN" >> "$LOG_FILE"
    
    # Check temperature thresholds
    if [ "$TEMP" -ge "$THROTTLE_TEMP" ]; then
        send_alert "CRITICAL" "GPU temperature ${TEMP}°C >= ${THROTTLE_TEMP}°C - THERMAL THROTTLING IMMINENT!"
        
        # Optional: Emergency shutdown of inference containers
        # Uncomment to enable automatic protection:
        # docker stop vllm-gpu 2>/dev/null || true
        # send_alert "ACTION" "Stopped vllm-gpu container for thermal protection"
        
    elif [ "$TEMP" -ge "$ALERT_TEMP" ]; then
        send_alert "WARNING" "GPU temperature ${TEMP}°C >= ${ALERT_TEMP}°C - Approaching thermal limit"
    fi
    
    # Check power anomalies (optional)
    if [ "${POWER%.*}" -gt 300 ]; then
        send_alert "WARNING" "GPU power draw ${POWER}W exceeds 300W - Check cooling"
    fi
    
    # Print status to console (every 5th sample)
    SAMPLE_COUNT=${SAMPLE_COUNT:-0}
    SAMPLE_COUNT=$((SAMPLE_COUNT + 1))
    if [ $((SAMPLE_COUNT % 5)) -eq 0 ]; then
        echo "[$(date +%H:%M:%S)] Temp: ${TEMP}°C | Power: ${POWER}W | Util: ${UTIL}% | VRAM: ${MEM_USED}/${MEM_TOTAL}MB | Fan: ${FAN}%"
    fi
    
    sleep "$SAMPLE_INTERVAL"
done
