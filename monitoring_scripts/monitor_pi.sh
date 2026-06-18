#!/bin/bash
# Monitoramento Raspberry Pi
OUTPUT_DIR="./logs"
mkdir -p "$OUTPUT_DIR"
METRICS_FILE="$OUTPUT_DIR/hardware_metrics.csv"
INTERVAL=${1:-1}

# Keep command output and numeric formatting locale-independent for comma-separated CSV.
export LC_ALL=C

if [ ! -f "$METRICS_FILE" ]; then
    echo "timestamp,cpu_temp_C,core_voltage_V,cpu_load_1min,cpu_load_5min,cpu_load_15min,cpu_usage_percent,mem_total_MB,mem_used_MB,mem_free_MB,mem_available_MB,mem_usage_percent" > "$METRICS_FILE"
fi

get_cpu_usage() {
    local cpu_stats_before=$(grep "^cpu " /proc/stat)
    sleep 1
    local cpu_stats_after=$(grep "^cpu " /proc/stat)

    local user_before=$(echo "$cpu_stats_before" | awk '{print $2}')
    local system_before=$(echo "$cpu_stats_before" | awk '{print $4}')
    local idle_before=$(echo "$cpu_stats_before" | awk '{print $5}')

    local user_after=$(echo "$cpu_stats_after" | awk '{print $2}')
    local system_after=$(echo "$cpu_stats_after" | awk '{print $4}')
    local idle_after=$(echo "$cpu_stats_after" | awk '{print $5}')

    local user_diff=$((user_after - user_before))
    local system_diff=$((system_after - system_before))
    local idle_diff=$((idle_after - idle_before))
    local total_diff=$((user_diff + system_diff + idle_diff))

    if [ $total_diff -gt 0 ]; then
        awk "BEGIN {printf \"%.2f\", ((($user_diff + $system_diff) / $total_diff) * 100)}"
    else
        echo "0"
    fi
}

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    TEMP=$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//;s/'\''C//' || echo "0")
    VOLTAGE=$(vcgencmd measure_volts core 2>/dev/null | sed 's/volt=//;s/V//' || echo "0")
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | sed 's/ //g')
    LOAD1=$(echo "$LOAD" | cut -d',' -f1)
    LOAD5=$(echo "$LOAD" | cut -d',' -f2)
    LOAD15=$(echo "$LOAD" | cut -d',' -f3)
    CPU_USAGE=$(get_cpu_usage)
    MEM_STATS=$(free -m | awk 'NR==2{printf "%s,%s,%s,%s,%.2f", $2,$3,$4,$7,($3/$2)*100}')
    echo "$TIMESTAMP,$TEMP,$VOLTAGE,$LOAD1,$LOAD5,$LOAD15,$CPU_USAGE,$MEM_STATS" >> "$METRICS_FILE"
    sleep $((INTERVAL - 1))
done
