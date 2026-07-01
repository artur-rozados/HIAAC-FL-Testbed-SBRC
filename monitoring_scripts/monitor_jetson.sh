#!/bin/bash
# Monitoramento NVIDIA Jetson
OUTPUT_DIR="./logs"
mkdir -p "$OUTPUT_DIR"
METRICS_FILE="$OUTPUT_DIR/hardware_metrics.csv"
TEGRASTATS_RAW="$OUTPUT_DIR/tegrastats_raw.log"
INTERVAL_MS=${1:-1000}
DEBUG=${DEBUG:-0}

# Keep command output and numeric formatting locale-independent for comma-separated CSV.
export LC_ALL=C

if [ ! -f "$METRICS_FILE" ]; then
    echo "timestamp,cpu_usage_percent,mem_used_MB,mem_total_MB,mem_usage_percent,gpu_usage_percent,temp_CPU_C,temp_GPU_C,temp_thermal_C,power_mW" > "$METRICS_FILE"
fi

tegrastats --interval $INTERVAL_MS 2>/dev/null | while IFS= read -r line; do
    echo "$line" >> "$TEGRASTATS_RAW"
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    CPU_USAGE=$(echo "$line" | grep -oP 'CPU \[\K[^\]]+' | tr ',' '\n' | grep -oP '\d+(?=%)' | awk '{sum+=$1; count++} END {if(count>0) printf "%.2f", sum/count; else print "0"}')
    [ -z "$CPU_USAGE" ] && CPU_USAGE="0"
    MEM_USED=$(echo "$line" | grep -oP 'RAM \K\d+(?=/)')
    MEM_TOTAL=$(echo "$line" | grep -oP 'RAM \d+/\K\d+')
    [ -z "$MEM_USED" ] && MEM_USED="0"
    [ -z "$MEM_TOTAL" ] && MEM_TOTAL="1"
    MEM_PERCENT=$(awk "BEGIN {printf \"%.2f\", ($MEM_USED/$MEM_TOTAL)*100}")
    GPU_USAGE=$(echo "$line" | grep -oP 'GR3D_FREQ \K\d+(?=%)')
    [ -z "$GPU_USAGE" ] && GPU_USAGE="0"
    # O tegrastats emite os rótulos térmicos em minúsculas (cpu@, gpu@, tj@).
    # Usamos -i (case-insensitive) para casar tanto maiúsculas quanto minúsculas
    # entre modelos de Jetson diferentes; senão a temperatura sai sempre 0.
    TEMP_CPU=$(echo "$line" | grep -oiP 'cpu@\K[\d.]+' | head -1)
    [ -z "$TEMP_CPU" ] && TEMP_CPU=$(echo "$line" | grep -oiP 'Tdiode[@=]\K[\d.]+' | head -1)
    [ -z "$TEMP_CPU" ] && TEMP_CPU=$(echo "$line" | grep -oiP 'tj[@=]\K[\d.]+' | head -1)
    [ -z "$TEMP_CPU" ] && TEMP_CPU=$(echo "$line" | grep -oiP 'CV[@=]\K[\d.]+' | head -1)
    [ -z "$TEMP_CPU" ] && TEMP_CPU="0"
    TEMP_GPU=$(echo "$line" | grep -oiP 'gpu@\K[\d.]+' | head -1)
    [ -z "$TEMP_GPU" ] && TEMP_GPU="0"
    TEMP_THERMAL=$(echo "$line" | grep -oiP 'thermal@\K[\d.]+' | head -1)
    [ -z "$TEMP_THERMAL" ] && TEMP_THERMAL=$(echo "$line" | grep -oiP 'tj@\K[\d.]+' | head -1)
    [ -z "$TEMP_THERMAL" ] && TEMP_THERMAL="0"
    POWER=$(echo "$line" | grep -oP 'VDD_IN \K\d+')
    [ -z "$POWER" ] && POWER="0"

    [ "$DEBUG" = "1" ] && echo "[DEBUG] TEMP_CPU=$TEMP_CPU (line: ${line:0:100}...)" >&2

    echo "$TIMESTAMP,$CPU_USAGE,$MEM_USED,$MEM_TOTAL,$MEM_PERCENT,$GPU_USAGE,$TEMP_CPU,$TEMP_GPU,$TEMP_THERMAL,$POWER" >> "$METRICS_FILE"
done
