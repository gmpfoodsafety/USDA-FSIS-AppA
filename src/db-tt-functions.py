#!/usr/bin/env python3
#
# db-tt-functions.py (Data - Time Temperature Functions)
#
# Plots one or more Temperature (1st column) and
# Time (min or sec or mixed) on 2nd .. Nth columns.
#

import csv
import sys
import os
import math

def parse_to_minutes(time_str):
    """
    Converts 'X min' or 'X sec' strings to float minutes.
    Strictly requires units; returns None on invalid format.
    """
    if not time_str or not time_str.strip():
        return None
    parts = time_str.strip().split()
    if len(parts) != 2:
        return None
    try:
        val = float(parts[0])
        unit = parts[1].lower()
        if "min" in unit:
            return val
        elif "sec" in unit:
            return val / 60.0
        else:
            return None
    except (ValueError, IndexError):
        return None

def sanitize(name):
    """Sanitizes column headers into valid Python function names."""
    return name.replace(" ", "_").replace(".", "_").replace("%", "pct").replace("(", "").replace(")", "").replace("-", "_")

def generate_interpolation_code(col_name, data_points):
    """Generates the text for t_vs_T and T_vs_t functions using log-linear interpolation."""
    # Ensure data is sorted by temperature
    data_points.sort(key=lambda x: x[0])
    safe_name = sanitize(col_name)
    
    lines = []
    
    # --- Function: Temperature (linear) to Time (linear) ---
    lines.append(f"def t_vs_T_{safe_name}(temp_c):")
    lines.append(f"    \"\"\"Calculates linear time (min) for a given temperature (C) using log-linear interpolation.\"\"\"")
    for i in range(len(data_points) - 1):
        T0, t0 = data_points[i]
        T1, t1 = data_points[i+1]
        log_t0, log_t1 = math.log10(t0), math.log10(t1)
        
        cond = f"if {T0} <= temp_c <= {T1}:" if i == 0 else f"elif {T0} < temp_c <= {T1}:"
        lines.append(f"    {cond}")
        lines.append(f"        log_t = {log_t0} + (temp_c - {T0}) * ({log_t1 - log_t0}) / ({T1 - T0})")
        lines.append(f"        return 10**log_t")
    lines.append("    return None\n")

    # --- Function: Time (linear) to Temperature (linear) ---
    lines.append(f"def T_vs_t_{safe_name}(time_min):")
    lines.append(f"    \"\"\"Calculates linear temperature (C) for a given time (min) using log-linear interpolation.\"\"\"")
    lines.append(f"    if time_min <= 0: return None")
    lines.append(f"    log_t_in = math.log10(time_min)")
    
    # For time-to-temp, we need to consider if time is increasing or decreasing with temp
    for i in range(len(data_points) - 1):
        T0, t0 = data_points[i]
        T1, t1 = data_points[i+1]
        log_t0, log_t1 = math.log10(t0), math.log10(t1)
        
        low_log, high_log = sorted([log_t0, log_t1])
        cond = f"if {low_log} <= log_t_in <= {high_log}:" if i == 0 else f"elif {low_log} < log_t_in <= {high_log}:"
        lines.append(f"    {cond}")
        lines.append(f"        return {T0} + (log_t_in - {log_t0}) * ({T1 - T0}) / ({log_t1 - log_t0})")
    lines.append("    return None\n")
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: db-tt-functions.py <input.csv>")
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            headers = [h.strip() for h in next(reader)]
            rows = list(reader)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        sys.exit(1)

    # Output Boilerplate
    print("#!/usr/bin/env python3")
    print("# Generated Time-Temperature Functions")
    print("import math\n")

    # Process each column starting from the second column
    for i in range(1, len(headers)):
        col_name = headers[i]
        points = []
        for row in rows:
            if i < len(row):
                t_min = parse_to_minutes(row[i])
                if t_min is not None and t_min > 0:
                    points.append((float(row[0]), t_min))
        
        if len(points) >= 2:
            print(generate_interpolation_code(col_name, points))
            print("# " + "-"*40 + "\n")

if __name__ == "__main__":
    main()
