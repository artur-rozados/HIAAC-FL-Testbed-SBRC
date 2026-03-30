#!/bin/bash
# Monitoramento Raspberry Pi
OUTPUT_DIR="./logs"
mkdir -p "$OUTPUT_DIR"
METRICS_FILE="$OUTPUT_DIR/hardware_metrics.csv"
INTERVAL=${1:-1}

# Keep command output and numeric formatting locale-independent for comma-separated CSV.
export LC_ALL=C

if [ ! -f "$METRICS_FILE" ]; then
    echo "timestamp,cpu_temp_C,core_voltage_V,cpu_load_1min,cpu_load_5min,cpu_load_15min,mem_total_MB,mem_used_MB,mem_free_MB,mem_available_MB,mem_usage_percent" > "$METRICS_FILE"
fi

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    TEMP=$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//;s/'\''C//' || echo "N/A")
    VOLTAGE=$(vcgencmd measure_volts core 2>/dev/null | sed 's/volt=//;s/V//' || echo "N/A")
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | sed 's/ //g')
    LOAD1=$(echo $LOAD | cut -d',' -f1)
    LOAD5=$(echo $LOAD | cut -d',' -f2)
    LOAD15=$(echo $LOAD | cut -d',' -f3)
    MEM_STATS=$(free -m | awk 'NR==2{printf "%s,%s,%s,%s,%.2f", $2,$3,$4,$7,($3/$2)*100}')
    echo "$TIMESTAMP,$TEMP,$VOLTAGE,$LOAD1,$LOAD5,$LOAD15,$MEM_STATS" >> "$METRICS_FILE"
    sleep $INTERVAL
done
