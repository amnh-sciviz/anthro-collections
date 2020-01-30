# -*- coding: utf-8 -*-

import argparse
from pprint import pprint
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-query', dest="QUERY", default="coll_id=4", help="Query string")
parser.add_argument('-name', dest="NAME", default="MexicoAndCentralAmerica", help="Unique name for filenames and directory names")
parser.add_argument('-py', dest="PYTHON_NAME", default="python3", help="Name of python command")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output command strings?")
a = parser.parse_args()

# First scrape the HTML
command = [a.PYTHON_NAME, 'scrape_html.py',
                '-query', a.QUERY,
                '-dir', "downloads/%s/page-%%s.html" % a.NAME]
if a.OVERWRITE:
    command.append('-overwrite')
print(" ".join(command))
if not a.PROBE:
    finished = subprocess.check_call(command)
print("========================================================")

# Then convert the HTML to .csv file
command = [a.PYTHON_NAME, 'html_to_csv.py',
                '-in', "downloads/%s/page-*.html" % a.NAME,
                '-out', "data/%s.csv" % a.NAME]
print(" ".join(command))
if not a.PROBE:
    finished = subprocess.check_call(command)
print("========================================================")

# Then write data summary
command = [a.PYTHON_NAME, 'data_summary.py',
                '-in', "data/%s.csv" % a.NAME,
                '-out', "reports/%s.txt" % a.NAME]
print(" ".join(command))
if not a.PROBE:
    finished = subprocess.check_call(command)
print("========================================================")
