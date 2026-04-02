This /src directory contains all the python scripts that were created to convert raw USDA FSIS Appendix A data (time-temperature tables) into a consolidated All.csv file and also to plot the raw data and create the final calculator .html file (HTML/CSS/Javascript).

Important python command line scripts in this folder are described as follows:

- db-tt-plot.py

This is the first script to use.  Reads raw input .csv data tables and outpus a consolidated .csv data table.

Full usage information may be obtained by passing the -h option:
```
db-tt-plot.py -h
usage: db-tt-plot.py [-h] [-t] [-l] [-d] [--sec] [-L] [-f FILTER] [-o OUTPUT] [-n] files [files ...]

Interactive plot for multiple CSV series.

positional arguments:
  files                 CSV files to process

optional arguments:
  -h, --help            show this help message and exit
  -t, --transpose       Temp on Y, Time on X
  -l, --legend          Move legend outside graph
  -d, --data            Show data points on lines
  --sec                 Show time in seconds instead of minutes
  -L, --log             Use logarithmic scale for the time axis
  -f FILTER, --filter FILTER
                        Only plot traces containing this string in their legend name
  -o OUTPUT, --output OUTPUT
                        Save consolidated data to CSV and exit
  -n, --names           Do not add filenames to column titles/legends
```

Converting all the USDA FSIS Appendix A tables (creatd manyally from PDF to .csv files first) into a master table can be done by executing:
```
db-tt-plot.py Meat-5.0-Log.csv Meat-6.5-Log.csv Meat-7.0-Log.csv Chicken-7.0-Log.csv Turkey-7.0-Log.csv -o All.csv
Consolidated data successfully saved to All.csv
```

Other options allow plotting graphs instead of generating a consolidated data table.  These options may also be used when passing in the final consolidated table.  Use th -f optiono to pass keywords that will limit or filter the series plotted, for example: -f chicken,meat.

- db-tt-functions.py

This file is not necessary.  It may be used to read the consolidated master table All.csv and produce a list of forward and reverse functions in Javascript .json format.  The script that generates the .html output does the same internally and includes the functions in the .html calculator page.  Running this script is only necessary to inspect and double check the syntax of the functions being generated.  Recommendation: do not use it.

Usage would be as follows. 
```
db-tt-functions.py All.csv > functions.txt
```

- db-tt-html-graph.py

This is the python scrpt that reads the final consolidated data table (All.csv) and outputs an .html file with the code for the lethality calculator.

Usage informationn may be obtained by passing -h:

```
db-tt-html-graph.py -h
usage: db-tt-html-graph.py [-h] [-o OUTPUT] input_csv

Generate a standalone HTML/JS USDA FSIS Appendix A Calculator.

positional arguments:
  input_csv             Path to the sparse CSV file.

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output HTML file path (default: input_filename.html).
```

To create the calculator self contained HTML web page file with all the HTML/CSS/Javascript that includes the design, UI, and all the calculation functions and graph plotting abilities you can run:

```
db-tt-html-graph.py All.csv -o calc
Successfully generated: calc.html
```
