#!/bin/bash
# ~/ai-idp/scripts/thermal-monitor.sh
# Lightweight GPU Thermal Monitor (Alternative to DCGM)
# Version: 2.0 | Date: 2026-01-12
#
# Features:
# - CSV logging with rotation
# - Temperature alerts (warning/critical)
# - Optional container shutdown on thermal emergency
# - Low overhead (~1% CPU)

set -euo pipefail

# Configuration
LOG_DIR="/var/log/ai-idp"
LOG_FILE="$LOG_DIR/gpu-thermal.csv"
ALERT_FILE="$LOG_DIR/alerts.log"
SAMPLE_INTERVAL=30          # Seconds between samples
ALERT_TEMP=85               # Warning threshold (Celsius)
THROTTLE_TEMP=90            # Critical threshold (Celsius)
MAX_LOG_LINES=100000        # Rotate after this many lines
RETENTION_DAYS=7            # Keep logs for this many days
EMERGENCY_SHUTDOWN=false    # Set true to auto-stop containers on critical

# Colors for terminal output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Create directories
setup_logging() {
    mkdir -p "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    # Initialize CSV if not exists
    if [ ! -f "$LOG_FILE" ]; then
        echo "timestamp,temp_c,power_w,util_pct,mem_used_mb,mem_total_mb,fan_pct,throttle_reason" > "$LOG_FILE"
        echo "GPU thermal logging initialized: $LOG_FILE"
    fi
}

# Rotate logs to prevent disk exhaustion
rotate_logs() {
    # Remove old rotated logs
    find "$LOG_DIR" -name "gpu-thermal.csv.*" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
    
    # Rotate current log if too large
    if [ -f "$LOG_FILE" ]; then
        local line_count=$(wc -l < "$LOG_FILE")
        if [ "$line_count" -gt "$MAX_LOG_LINES" ]; then
            local rotate_file="$LOG_FILE.$(date +%Y%m%d-%H%M%S)"
            mv "$LOG_FILE" "$rotate_file"
            gzip "$rotate_file" &
            echo "timestamp,temp_c,power_w,util_pct,mem_used_mb,mem_total_mb,fan_pct,throttle_reason" > "$LOG_FILE"
            echo "Log rotated to: ${rotate_file}.gz"
        fi
    fi
}

# Log alert message
log_alert() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    
    echo "[$timestamp] $level: $message" >> "$ALERT_FILE"
    
    case "$level" in
        "CRITICAL")
            echo -e "${RED}[$timestamp] $level: $message${NC}" >&2
            ;;
        "WARNING")
            echo -e "${YELLOW}[$timestamp] $level: $message${NC}" >&2
            ;;
        *)
            echo "[$timestamp] $level: $message"
            ;;
    esac
}

# Emergency container shutdown
emergency_shutdown() {
    if [ "$EMERGENCY_SHUTDOWN" = true ]; then
        log_alert "EMERGENCY" "Initiating emergency container shutdown..."
        docker stop vllm-gpu llamacpp-70b 2>/dev/null || true
        log_alert "EMERGENCY" "Inference containers stopped. Manual restart required."
    else
        log_alert "CRITICAL" "Emergency shutdown disabled. Consider stopping containers manually."
    fi
}

# Main monitoring loop
monitor_gpu() {
    local consecutive_critical=0
    
    while true; do
        local timestamp=$(date -Iseconds)
        
        # Query GPU metrics
        local metrics=$(nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total,fan.speed,clocks_event_reasons.hw_thermal_slowdown \
            --format=csv,noheader,nounits 2>/dev/null || echo "")
        
        if [ -n "$metrics" ]; then
            # Parse metrics
            local temp=$(echo "$metrics" | cut -d',' -f1 | tr -d ' ')
            local power=$(echo "$metrics" | cut -d',' -f2 | tr -d ' ')
            local util=$(echo "$metrics" | cut -d',' -f3 | tr -d ' ')
            local mem_used=$(echo "$metrics" | cut -d',' -f4 | tr -d ' ')
            local mem_total=$(echo "$metrics" | cut -d',' -f5 | tr -d ' ')
            local fan=$(echo "$metrics" | cut -d',' -f6 | tr -d ' ')
            local throttle=$(echo "$metrics" | cut -d',' -f7 | tr -d ' ')
            
            # Log to CSV
            echo "$timestamp,$temp,$power,$util,$mem_used,$mem_total,$fan,$throttle" >> "$LOG_FILE"
            
            # Temperature alerts
            if [ -n "$temp" ] && [ "$temp" -ge "$THROTTLE_TEMP" ] 2>/dev/null; then
                consecutive_critical=$((consecutive_critical + 1))
                log_alert "CRITICAL" "GPU at ${temp}°C - THERMAL THROTTLING! (Power: ${power}W, Util: ${util}%)"
                
                # Emergency shutdown after 3 consecutive critical readings
                if [ "$consecutive_critical" -ge 3 ]; then
                    emergency_shutdown
                fi
            elif [ -n "$temp" ] && [ "$temp" -ge "$ALERT_TEMP" ] 2>/dev/null; then
                consecutive_critical=0
                log_alert "WARNING" "GPU at ${temp}°C - Approaching thermal limit (Power: ${power}W, Fan: ${fan}%)"
            else
                consecutive_critical=0
            fi
            
            # Check for thermal throttling flag from nvidia-smi
            if [ "$throttle" = "Active" ] || [ "$throttle" = "Yes" ]; then
                log_alert "WARNING" "GPU thermal throttling active! Reduce workload."
            fi
        else
            log_alert "ERROR" "Failed to query GPU metrics. Is nvidia-smi available?"
        fi
        
        sleep "$SAMPLE_INTERVAL"
    done
}

# Status display function
show_status() {
    echo "GPU Thermal Monitor Status"
    echo "=========================="
    
    if [ -f "$LOG_FILE" ]; then
        local last_entry=$(tail -1 "$LOG_FILE")
        echo "Last reading: $last_entry"
        echo ""
        echo "Recent alerts (last 5):"
        tail -5 "$ALERT_FILE" 2>/dev/null || echo "  No alerts"
    else
        echo "No data collected yet"
    fi
}

# Cleanup on exit
cleanup() {
    echo ""
    log_alert "INFO" "Thermal monitor stopped"
    exit 0
}

# Main entry point
main() {
    trap cleanup SIGTERM SIGINT
    
    case "${1:-run}" in
        run)
            echo "Starting GPU Thermal Monitor..."
            echo "Log file: $LOG_FILE"
            echo "Alert threshold: ${ALERT_TEMP}°C (warning), ${THROTTLE_TEMP}°C (critical)"
            echo "Sample interval: ${SAMPLE_INTERVAL}s"
            echo "Press Ctrl+C to stop"
            echo ""
            
            setup_logging
            rotate_logs
            monitor_gpu
            ;;
        status)
            show_status
            ;;
        rotate)
            rotate_logs
            echo "Log rotation complete"
            ;;
        *)
            echo "Usage: $0 {run|status|rotate}"
            exit 1
            ;;
    esac
}

main "$@"
