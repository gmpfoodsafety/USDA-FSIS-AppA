#!/usr/bin/env python3
#
# db-tt-html.py (Data - Time Temperature HTML Generator)
#
# Generates a standalone HTML/JS calculator for piece-wise log-linear 
# interpolation of Time (min) and Temperature (C) data.
#
# The db-tt-html.py script is a data-processing tool that converts static CSV tables 
# into a standalone, interactive web application for calculating thermal inactivation. 
# It ingests time-temperature data—specifically handling units like "sec" or "min" and 
# ignoring empty cells—and embeds this data into a single HTML file as a JSON object. 
# The resulting HTML interface allows users to select a specific product or log-reduction 
# target from a dropdown menu and perform real-time, reciprocal calculations between 
# Processing Time and Processing Temperature. Using embedded JavaScript, it performs 
# piece-wise linear interpolation in log-time and linear-temperature space (consistent 
# with USDA FSIS Appendix A standards), ensuring that when one value is entered, the other 
# is instantly updated to reflect the necessary parameters for food safety compliance.
#

import csv
import sys
import os
import math
import json

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
    except (ValueError, IndexError):
        return None
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 db-tt-html.py <file1.csv> [file2.csv ...]")
        sys.exit(1)

    # Dictionary to hold data for each column: { "Column Name": [[temp, time_min], ...] }
    all_data = {}

    for filepath in sys.argv[1:]:
        try:
            with open(filepath, 'r') as f:
                reader = csv.reader(f)
                headers = [h.strip() for h in next(reader)]
                rows = list(reader)
                
                for i in range(1, len(headers)):
                    col_name = headers[i]
                    points = []
                    for row in rows:
                        if i < len(row):
                            t_min = parse_to_minutes(row[i])
                            if t_min is not None and t_min > 0:
                                points.append([float(row[0]), t_min])
                    
                    if len(points) >= 2:
                        points.sort(key=lambda x: x[0]) # Sort by Temp
                        all_data[col_name] = points
        except Exception as e:
            sys.stderr.write(f"Error reading {filepath}: {e}\n")

    if not all_data:
        sys.stderr.write("No valid data found to generate HTML.\n")
        sys.exit(1)

    options_html = "".join([f'<option value="{h}">{h}</option>' for h in all_data.keys()])
    json_data = json.dumps(all_data)

    # Using a standard string and .replace() to avoid f-string SyntaxErrors with CSS/JS braces
    html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Time-Temperature Inactivation Calculator</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
        .container { max-width: 600px; background: #f9f9f9; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 1px solid #eee; }
        .field { margin-bottom: 20px; }
        label { display: block; font-weight: 600; margin-bottom: 8px; font-size: 0.9em; text-transform: uppercase; color: #555; }
        select, input { width: 100%; padding: 12px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 6px; font-size: 1em; }
        select:focus, input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.25); }
        .note { font-size: 0.85em; color: #666; margin-top: 25px; border-top: 1px solid #ddd; padding-top: 15px; font-style: italic; }
        h2 { margin-top: 0; color: #222; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Inactivation Calculator</h2>
        
        <div class="field">
            <label for="product">Product Inactivation:</label>
            <select id="product" onchange="calculate('temp')">
                {{OPTIONS_PLACEHOLDER}}
            </select>
        </div>

        <div class="field">
            <label for="time">Processing Time (min):</label>
            <input type="number" id="time" step="any" placeholder="Enter minutes" oninput="calculate('temp')">
        </div>

        <div class="field">
            <label for="temp">Processing Temperature (C):</label>
            <input type="number" id="temp" step="any" placeholder="Enter Celsius" oninput="calculate('time')">
        </div>

        <div class="note">
            * Logic: Piece-wise linear interpolation (Log Time vs. Linear Temperature).<br>
            * Regulatory Reference: USDA FSIS Appendix A.
        </div>
    </div>

    <script>
        const dataMap = {{DATA_PLACEHOLDER}};

        function calculate(target) {
            const product = document.getElementById('product').value;
            const points = dataMap[product];
            const timeField = document.getElementById('time');
            const tempField = document.getElementById('temp');

            if (target === 'temp') {
                const tMin = parseFloat(timeField.value);
                if (isNaN(tMin) || tMin <= 0) { tempField.value = ""; return; }
                const logTIn = Math.log10(tMin);
                
                for (let i = 0; i < points.length - 1; i++) {
                    let [T0, t0] = points[i];
                    let [T1, t1] = points[i+1];
                    let logt0 = Math.log10(t0), logt1 = Math.log10(t1);
                    
                    let minL = Math.min(logt0, logt1), maxL = Math.max(logt0, logt1);
                    if (logTIn >= minL && logTIn <= maxL) {
                        let res = T0 + (logTIn - logt0) * (T1 - T0) / (logt1 - logt0);
                        tempField.value = res.toFixed(2);
                        return;
                    }
                }
                tempField.value = "Out of Range";
            } else {
                const TVal = parseFloat(tempField.value);
                if (isNaN(TVal)) { timeField.value = ""; return; }

                for (let i = 0; i < points.length - 1; i++) {
                    let [T0, t0] = points[i];
                    let [T1, t1] = points[i+1];
                    if (TVal >= T0 && TVal <= T1) {
                        let logt0 = Math.log10(t0), logt1 = Math.log10(t1);
                        let logRes = logt0 + (TVal - T0) * (logt1 - logt0) / (T1 - T0);
                        timeField.value = Math.pow(10, logRes).toFixed(2);
                        return;
                    }
                }
                timeField.value = "Out of Range";
            }
        }
    </script>
</body>
</html>
"""

    output = html_template.replace("{{OPTIONS_PLACEHOLDER}}", options_html)
    output = output.replace("{{DATA_PLACEHOLDER}}", json_data)
    print(output)

if __name__ == "__main__":
    main()
