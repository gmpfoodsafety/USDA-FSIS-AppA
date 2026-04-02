#!/usr/bin/env python3
#
# db-tt-html-graph.py
#
# DESCRIPTION:
# Generates a standalone USDA FSIS Appendix A Salmonella Inactivation Calculator.
# Converts sparse CSV data into a dynamic HTML/JS tool with real-time visualization.
#
# KEY FEATURES & IMPROVEMENTS:
# - Piecewise Log-Linear Interpolation: Ensures 100% mathematical alignment between 
#   the calculator values and the FSIS lethality tables.
# - High-Resolution Curve Rendering: The blue lethality curve is drawn using 100 
#   sub-points per segment to prevent "point drifting" at low time values (e.g., <11s).
# - Continuous Proportional Scaling: The X-axis (Time) uses a dynamic 1.3x - 1.5x 
#   buffer, allowing for a "smart zoom" on fast processes while showing the full 
#   curve for long-duration processes.
# - Strict Regulatory Clamping: All user inputs (Time/Temp) are automatically 
#   clamped to the minimum/maximum table values to prevent illegal process parameters.
# - State Preservation: Current processing time is preserved when switching between 
#   different product species/log-reductions.
# - High-Visibility UI: Includes bold red intersection labels, synchronized crosshairs, 
#   and enlarged axis labels for industrial/laboratory readability.
# - Robust File Handling: Includes automatic .html extension tagging and interactive 
#   overwrite protection.
#
import csv
import json
import argparse
import sys
import os

def parse_to_minutes(time_str):
    if not time_str or not time_str.strip(): 
        return None
    clean_str = time_str.replace(',', '').strip()
    parts = clean_str.split()
    if len(parts) < 2: return None
    try:
        val = float(parts[0])
        unit = parts[1].lower()
        if "min" in unit: return val
        if "sec" in unit: return val / 60.0
        return None
    except (ValueError, IndexError):
        return None

def main():
    parser = argparse.ArgumentParser(description="Generate a standalone HTML/JS USDA FSIS Appendix A Calculator.")
    parser.add_argument("input_csv", help="Path to the sparse CSV file.")
    parser.add_argument("-o", "--output", help="Output HTML file path (default: input_filename.html).")
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        base = os.path.splitext(args.input_csv)[0]
        output_path = base + ".html"
    elif not output_path.lower().endswith(".html"):
        output_path += ".html"

    if os.path.exists(output_path):
        ans = input(f"File '{output_path}' already exists. Overwrite? (y/n): ").lower()
        if ans != 'y':
            print("Aborted.")
            sys.exit(0)

    all_data = {}
    try:
        with open(args.input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            headers = [h.strip() for h in next(reader)]
            rows = list(reader)
            for i in range(1, len(headers)):
                points = []
                for row in rows:
                    if i < len(row) and row[i].strip():
                        t_min = parse_to_minutes(row[i])
                        if t_min is not None:
                            points.append([round(float(row[0]), 2), t_min])
                if len(points) >= 2:
                    points.sort(key=lambda x: x[0])
                    all_data[headers[i]] = points
    except Exception as e:
        sys.stderr.write(f"Error reading CSV: {e}\n")
        sys.exit(1)

    options_html = "".join([f'<option value="{h}">{h}</option>' for h in all_data.keys()])

    html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>USDA FSIS Appendix A Calculator</title>
<style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 20px; color: #333; background: #f0f2f5; display: flex; flex-direction: column; align-items: center; }
    .container { width: 950px; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); margin-bottom: 20px; box-sizing: border-box; }
    .input-row { display: flex; gap: 15px; margin-bottom: 15px; }
    .field { flex: 1; }
    label { display: block; font-weight: 700; font-size: 0.75rem; margin-bottom: 8px; color: #666; text-transform: uppercase; letter-spacing: 0.05em; }
    input, select { width: 100%; padding: 12px; box-sizing: border-box; border: 2px solid #eee; border-radius: 8px; font-size: 1rem; background: #fafafa; }
    .warning { color: #cf1322; font-size: 0.75rem; font-weight: 600; margin-top: 4px; display: none; }
    canvas { width: 100%; height: auto; display: block; background: #fff; border-radius: 4px; }
</style>
</head>
<body onload="init(true)">
    <h1>USDA FSIS Appendix A Calculator</h1>
    <div class="container">
        <div class="input-row">
            <div class="field">
                <label>Product / Lethality</label>
                <select id="product" onchange="init(false)">{{OPTIONS}}</select>
            </div>
        </div>
        <div class="input-row">
            <div class="field"><label>Temp (°C)</label><input type="number" id="temp_c" step="0.1" oninput="sync('c', this.value)"><div id="warn_c" class="warning">Clamped to Range</div></div>
            <div class="field"><label>Temp (°F)</label><input type="number" id="temp_f" step="0.1" oninput="sync('f', this.value)"></div>
            <div class="field"><label>Time (Min)</label><input type="number" id="time_m" step="0.01" oninput="sync('m', this.value)"><div id="warn_m" class="warning">Clamped to Range</div></div>
            <div class="field"><label>Time (Sec)</label><input type="number" id="time_s" step="1" oninput="sync('s', this.value)"></div>
        </div>
    </div>
    <div class="container">
        <h2 id="graph-title" style="margin:0 0 20px 0; font-size:1.4rem;">Process Lethality</h2>
        <canvas id="graph" width="1600" height="900"></canvas>
    </div>

<script>
const dataMap = {{DATA}};
const canvas = document.getElementById('graph'), ctx = canvas.getContext('2d');
const padding = { top: 60, right: 120, bottom: 120, left: 180 };

function init(first) {
    const p = document.getElementById('product').value;
    const pts = dataMap[p];
    document.getElementById('graph-title').innerText = `Process Lethality for ${p}`;
    
    const existingTime = parseFloat(document.getElementById('time_m').value);
    if (first || isNaN(existingTime)) {
        document.getElementById('temp_c').value = pts[0][0];
        sync('c', pts[0][0]);
    } else {
        calculate('temp'); 
    }
}

function sync(unit, val) {
    const v = parseFloat(val); if (isNaN(v)) return;
    if (unit === 'm') { document.getElementById('time_s').value = Math.round(v * 60); calculate('temp'); }
    else if (unit === 's') { document.getElementById('time_m').value = (v / 60).toFixed(3); calculate('temp'); }
    else if (unit === 'c') { document.getElementById('temp_f').value = (v * 9/5 + 32).toFixed(1); calculate('time'); }
    else if (unit === 'f') { const c = (v - 32) * 5/9; document.getElementById('temp_c').value = c.toFixed(2); calculate('time'); }
}

function calculate(target) {
    const pts = dataMap[document.getElementById('product').value];
    const tm = document.getElementById('time_m'), tc = document.getElementById('temp_c'), tf = document.getElementById('temp_f');
    const wm = document.getElementById('warn_m'), wc = document.getElementById('warn_c');
    
    const minT = pts[0][0], maxT = pts[pts.length-1][0];
    const times = pts.map(p => p[1]);
    const minM = Math.min(...times), maxM = Math.max(...times);

    wm.style.display = wc.style.display = 'none';

    if (target === 'time') {
        let c = parseFloat(tc.value);
        if (c < minT) { c = minT; tc.value = c.toFixed(2); wc.style.display = 'block'; }
        if (c > maxT) { c = maxT; tc.value = c.toFixed(2); wc.style.display = 'block'; }
        tf.value = (c * 9/5 + 32).toFixed(1);
        for (let i = 0; i < pts.length - 1; i++) {
            let [T0, t0] = pts[i], [T1, t1] = pts[i+1];
            if (c >= T0 && c <= T1) {
                const res = Math.pow(10, Math.log10(t0) + (c - T0) * (Math.log10(t1) - Math.log10(t0)) / (T1 - T0));
                tm.value = res.toFixed(3); document.getElementById('time_s').value = Math.round(res * 60);
                break;
            }
        }
    } else {
        let m = parseFloat(tm.value);
        if (m < minM) { m = minM; tm.value = m.toFixed(3); wm.style.display = 'block'; }
        if (m > maxM) { m = maxM; tm.value = m.toFixed(3); wm.style.display = 'block'; }
        document.getElementById('time_s').value = Math.round(m * 60);
        const logM = Math.log10(m);
        for (let i = 0; i < pts.length - 1; i++) {
            let [T0, t0] = pts[i], [T1, t1] = pts[i+1];
            let l0 = Math.log10(t0), l1 = Math.log10(t1);
            if (logM >= Math.min(l0, l1) && logM <= Math.max(l0, l1)) {
                const res = T0 + (logM - l0) * (T1 - T0) / (l1 - l0);
                tc.value = res.toFixed(2); tf.value = (res * 9/5 + 32).toFixed(1);
                break;
            }
        }
    }
    drawGraph();
}

function drawGraph() {
    const pts = dataMap[document.getElementById('product').value];
    const curM = parseFloat(document.getElementById('time_m').value);
    const curC = parseFloat(document.getElementById('temp_c').value);
    const curF = curC * 9/5 + 32;
    if (isNaN(curM) || isNaN(curC)) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const xMax = Math.max(curM * 1.5, 0.5); 
    const minF = pts[0][0] * 9/5 + 32, maxF = pts[pts.length-1][0] * 9/5 + 32;

    const getX = (m) => padding.left + (m / xMax) * (canvas.width - padding.left - padding.right);
    const getY = (c) => {
        const f = c * 9/5 + 32;
        return (canvas.height - padding.bottom) - ((f - minF) / (maxF - minF)) * (canvas.height - padding.top - padding.bottom);
    };

    // Grid and Axes
    ctx.strokeStyle = '#eee'; ctx.lineWidth = 1; ctx.font = "24px sans-serif"; ctx.fillStyle = "#888";
    for (let i = 0; i <= 5; i++) {
        let f = minF + (maxF - minF) * (i / 5);
        let y = getY((f - 32) * 5 / 9);
        ctx.textAlign = "right"; ctx.fillText(f.toFixed(1) + "°F", padding.left - 30, y + 8);
        ctx.beginPath(); ctx.moveTo(padding.left, y); ctx.lineTo(canvas.width - padding.right, y); ctx.stroke();
    }
    for (let i = 0; i <= 5; i++) {
        let m = (xMax * i) / 5;
        let x = getX(m);
        ctx.textAlign = "center"; 
        ctx.fillText(m < 1 ? Math.round(m*60)+'s' : m.toFixed(1)+'m', x, canvas.height - padding.bottom + 45);
        ctx.beginPath(); ctx.moveTo(x, canvas.height - padding.bottom); ctx.lineTo(x, padding.top); ctx.stroke();
    }

    // High-Resolution Log-Linear Curve Drawing
    ctx.strokeStyle = '#007bff'; ctx.lineWidth = 6; ctx.lineJoin = 'round';
    ctx.beginPath();
    for (let i = 0; i < pts.length - 1; i++) {
        let [T0, t0] = pts[i], [T1, t1] = pts[i+1];
        let l0 = Math.log10(t0), l1 = Math.log10(t1);
        for (let j = 0; j <= 100; j++) {
            let temp = T0 + (T1 - T0) * (j / 100);
            let time = Math.pow(10, l0 + (temp - T0) * (l1 - l0) / (T1 - T0));
            if (i === 0 && j === 0) ctx.moveTo(getX(time), getY(temp));
            else ctx.lineTo(getX(time), getY(temp));
        }
    }
    ctx.stroke();

    // Red Interaction Layer
    const px = getX(curM), py = getY(curC);
    ctx.setLineDash([8, 8]); ctx.strokeStyle = '#ff4d4f'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(px, canvas.height - padding.bottom); ctx.lineTo(px, py); ctx.lineTo(padding.left, py); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = '#ff4d4f'; ctx.beginPath(); ctx.arc(px, py, 14, 0, Math.PI*2); ctx.fill();
    ctx.font = "bold 36px sans-serif";
    ctx.textAlign = "right"; ctx.fillText(curF.toFixed(1) + "°F", padding.left - 30, py + 12);
    ctx.textAlign = "center"; ctx.fillText(curM < 1 ? Math.round(curM*60) + 's' : curM.toFixed(2) + 'm', px, canvas.height - padding.bottom + 95);
}
</script>
</body>
</html>"""

    final_html = html_template.replace("{{OPTIONS}}", options_html).replace("{{DATA}}", json.dumps(all_data))
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"Successfully generated: {output_path}")

if __name__ == "__main__":
    main()
