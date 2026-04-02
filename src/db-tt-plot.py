#!/usr/bin/env python3
#
# db-tt-plot.py (Data - Time Temperature Plot)
#
# Plots one or more Temperature (1st column) and
# Time (min or sec or mixed) on 2nd .. Nth colmuns.
#

import csv
import argparse
import os
import matplotlib.pyplot as plt
import sys

def parse_to_minutes(time_str, filepath):
    """
    Converts 'X min' or 'X sec' strings to float minutes.
    Strictly requires units; exits on invalid format or missing units.
    """
    parts = time_str.strip().split()

    if len(parts) != 2:
        print(f"Error: Invalid format at {filepath}: Expected value followed by 'min' or 'sec' (e.g., '10 min')")
        sys.exit(1)

    try:
        val = float(parts[0])
        unit = parts[1].lower()

        if "min" in unit:
            return val
        elif "sec" in unit:
            return val / 60.0
        else:
            print(f"Error: Unknown unit '{parts[1]}' at {filepath}: Only 'min' and 'sec' are accepted")
            sys.exit(1)

    except ValueError:
        print(f"Error: Non-numeric value '{parts[0]}' at {filepath}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Interactive plot for multiple CSV series.")
    parser.add_argument("files", nargs="+", help="CSV files to process")
    parser.add_argument("-t", "--transpose", action="store_true", help="Temp on Y, Time on X")
    parser.add_argument("-l", "--legend", action="store_true", help="Move legend outside graph")
    parser.add_argument("-d", "--data", action="store_true", help="Show data points on lines")
    parser.add_argument("--sec", action="store_true", help="Show time in seconds instead of minutes")
    parser.add_argument("-L", "--log", action="store_true", help="Use logarithmic scale for the time axis")
    parser.add_argument("-f", "--filter", type=str, help="Only plot traces containing this string in their legend name")
    parser.add_argument("-o", "--output", type=str, help="Save consolidated data to CSV and exit")
    parser.add_argument("-n", "--names", action="store_true", help="Do not add filenames to column titles/legends")
    args = parser.parse_args()

    all_series = []
    all_temps = set()
    global_temp_header = "Temperature"

    for filepath in args.files:
        fname = os.path.splitext(os.path.basename(filepath))[0]
        try:
            with open(filepath, 'r') as f:
                lines = [line.strip() for line in f if line.strip()]
                if not lines: continue
                reader = csv.reader(lines, skipinitialspace=True)
                headers = [h.strip() for h in next(reader)]
                rows = list(reader)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            sys.exit(1)

        global_temp_header = headers[0]
        
        # Process each time column
        for i in range(1, len(headers)):
            series_map = {}
            col_header = headers[i]
            
            # Determine Label based on --names flag
            if args.names:
                label = col_header
            else:
                if len(headers) == 2:
                    label = fname
                else:
                    label = f"{fname} ({col_header})"

            for row in rows:
                try:
                    time_raw = row[i].strip()
                    if not time_raw: continue
                    
                    t_val = float(row[0])
                    time_sec = parse_to_minutes(time_raw, filepath) * 60.0
                    series_map[t_val] = int(round(time_sec))
                    all_temps.add(t_val)
                except (ValueError, IndexError):
                    continue
            
            if series_map:
                all_series.append({"label": label, "data": series_map})

    # --- CSV Export Logic ---
    if args.output:
        out_path = args.output if args.output.lower().endswith(".csv") else args.output + ".csv"
        
        if os.path.exists(out_path):
            try:
                choice = input(f"Warning: '{out_path}' already exists. Overwrite? [Y/n]: ").strip().lower()
                if choice and choice != 'y':
                    print("Export cancelled.")
                    sys.exit(0)
            except EOFError:
                sys.exit(0)

        sorted_temps = sorted(list(all_temps))
        series_labels = [s["label"] for s in all_series]

        with open(out_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([global_temp_header] + series_labels)

            for temp in sorted_temps:
                row = [temp]
                for s in all_series:
                    time_val = s["data"].get(temp, "")
                    row.append(f"{time_val} sec" if time_val != "" else "")
                writer.writerow(row)
        
        print(f"Consolidated data successfully saved to {out_path}")
        return

    # --- Plotting Logic ---
    if not all_series:
        print("No valid data found to plot.")
        sys.exit(0)

    fig, ax = plt.subplots(figsize=(12, 6))
    time_unit = "seconds" if args.sec else "minutes"
    time_factor = 1.0 if args.sec else (1.0 / 60.0)
    marker_style = 'o' if args.data else None
    plot_lines = []

    for s in all_series:
        label = s["label"]
        if args.filter and args.filter not in label:
            continue
        
        sorted_points = sorted(s["data"].items())
        p_temps = [p[0] for p in sorted_points]
        p_times = [p[1] * time_factor for p in sorted_points]

        if args.transpose:
            ln, = ax.plot(p_times, p_temps, label=label, marker=marker_style, markersize=4)
        else:
            ln, = ax.plot(p_temps, p_times, label=label, marker=marker_style, markersize=4)
        plot_lines.append(ln)

    if args.transpose:
        ax.set_xlabel(f"Time ({time_unit})")
        ax.set_ylabel(global_temp_header)
        if args.log: ax.set_xscale('log')
    else:
        ax.set_xlabel(global_temp_header)
        ax.set_ylabel(f"Time ({time_unit})")
        if args.log: ax.set_yscale('log')

    if args.legend:
        leg = ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize='small')
    else:
        leg = ax.legend(loc='best', fontsize='small')

    map_legend_to_ax = {}
    leg_lines = leg.get_lines()
    leg_texts = leg.get_texts()

    for i, orig_line in enumerate(plot_lines):
        for obj in [leg_lines[i], leg_texts[i]]:
            obj.set_picker(True)
            if hasattr(obj, 'set_pickradius'): obj.set_pickradius(8)
            map_legend_to_ax[obj] = orig_line

    def on_pick(event):
        orig_line = map_legend_to_ax.get(event.artist)
        if not orig_line: return
        visible = not orig_line.get_visible()
        orig_line.set_visible(visible)
        for obj, line in map_legend_to_ax.items():
            if line == orig_line:
                obj.set_alpha(1.0 if visible else 0.2)
        fig.canvas.draw()

    fig.canvas.mpl_connect('pick_event', on_pick)
    ax.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
