# -*- coding: utf-8 -*-

import argparse
import collections
import math
import os
from pprint import pprint
import sys

import lib.io_utils as io
import lib.list_utils as lu
import lib.math_utils as mu

# input
parser = argparse.ArgumentParser()
parser.add_argument("-in", dest="INPUT_FILE", default="data/processed/MexicoAndCentralAmerica_cleaned.csv", help="File generated by clean_data.py")
parser.add_argument("-out", dest="OUTPUT_FILE", default="data/processed/MexicoAndCentralAmerica_geotag.csv", help="Output csv file")
a = parser.parse_args()

# Make sure output dirs exist
io.makeDirectories([a.OUTPUT_FILE])

fieldNames, items = io.readCsv(a.INPUT_FILE)
itemCount = len(items)

items = [item for item in items if len(item["Locale"].strip()) > 0 and len(item["Country"].strip()) > 0]
for i, item in enumerate(items):
    items[i]["LookupString"] = item["Locale"]
lookupTable = lu.createLookup(items, "LookupString")

values = [item["LookupString"] for item in items]
counter = collections.Counter(values)
counts = counter.most_common()

rows = []
for value, count in counts:
    if len(str(value).strip()) < 1:
        continue
    row = {}
    row["geoname"] = value

    item = lookupTable[value]
    row["id"] = item["Id"]
    row["country"] = item["Country"]
    if not (item["Latitude"] == 0 and item["Longitude"] == 0):
        row["latitude"] = item["Latitude"]
        row["longitude"] = item["Longitude"]
    rows.append(row)

io.writeCsv(a.OUTPUT_FILE, rows, ["id", "geoname", "latitude", "longitude", "country"])
