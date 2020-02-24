# -*- coding: utf-8 -*-

import argparse
import collections
from datetime import datetime
import glob
import math
import os
from pprint import pprint
import re
import sys

import lib.io_utils as io
import lib.list_utils as lu
import lib.math_utils as mu

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="data/*.csv", help="File generated by html_to_csv.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="data/processed/all_normalized.csv", help="Output csv file")
a = parser.parse_args()

# Make sure output dirs exist
io.makeDirectories([a.OUTPUT_FILE])

items = []
fieldNames = []

if "*" in a.INPUT_FILE:
    files = glob.glob(a.INPUT_FILE)
    for fn in files:
        fFieldNames, fItems = io.readCsv(fn)
        # Infer region from filename
        for j, fitem in enumerate(fItems):
            fItems[j]["Region"] = re.sub(r'(?<!^)(?=[A-Z])', ' ', os.path.basename(fn).split(".")[0])
        fieldNames += fFieldNames
        items += fItems
    fieldNames = lu.unique(fieldNames)

else:
    fieldNames, items = io.readCsv(a.INPUT_FILE)

itemCount = len(items)

# this is where the normalized data will go
cleanedItems = [{
    "Catalog No": item["Catalog No"],
    "Filename": os.path.basename(item["Thumb URL"]),
    "Region": item["Region"],
    "Acquisition Year": 9999,
    "Acquisition Type": "Unknown",
    "Acquisition Era": "Unknown",
    "Acquisition Year Confidence": 0,
    "Acquisition Type Confidence": 0,
    "Country": "",
    "Country Confidence": 0,
    "Hall": "",
    "Donor": "",
    "Donor Confidence": 0,
    "Expedition": "",
    "Latitude": 9999,
    "Longitude": 9999
} for item in items]

# Debugging...
# lu.countValues(cleanedItems, "Region")
# sys.exit()

##############################################
# STEP 1: retrieve year and acquisition type #
##############################################

validYearEnd = int(datetime.now().year)
def isValidYear(year):
    global validYearEnd
    validYearStart = 1800
    return isinstance(year, (int,)) and validYearStart <= year <= validYearEnd

# lu.countValues(items, "Acquisition Year")
# sys.exit()
datePattern = re.compile("([12][0-9]{3})(\-[12][0-9]{3})?( \[[A-Z,\? ]+\])?")
acquisitionTypeSynonyms = [
    ("MUSEUM EXPEDITION", "EXPEDITION"),
    ("FIELD PURCHASE", "PURCHASE"),
    ("MUSEUM TRANSFER", "TRANSFER")
]

for i, item in enumerate(items):
    year = item["Acquisition Year"]
    yearStr = str(year).strip()
    if len(yearStr) < 1:
        continue

    if isValidYear(year):
        cleanedItems[i]["Acquisition Year"] = year
        continue

    # Try to match against pattern
    matches = datePattern.match(yearStr)

    if not matches:
        print("Could not match pattern against string: %s" % yearStr)
        continue

    acquisitionYear = int(matches.group(1))
    yearConfidence = 1.0
    typeConfidence = 1.0
    # Check for year range
    aquisitionYearRangeEnd = ""
    if matches.group(2) is not None:
        aquisitionYearRangeEnd = int(matches.group(2).strip("-"))
    # Check for acquisition type
    acquisitionType = ""
    if matches.group(3) is not None:
        acquisitionType = matches.group(3).strip("[] ")
    # Check for question marks
    if "?" in acquisitionType:
        acquisitionType = acquisitionType.replace("?", "").strip()
        typeConfidence *= 0.5
    # Check for a list; just take the first one
    if "," in acquisitionType:
        acquisitionType = acquisitionType.split(", ")[0]
        typeConfidence *= 0.5

    # Check for valid year range
    if isValidYear(acquisitionYear) and isValidYear(aquisitionYearRangeEnd):
        # Just take the mean
        acquisitionYear = int(round(0.5 * (acquisitionYear + aquisitionYearRangeEnd)))
        yearConfidence *= 0.5
    elif not isValidYear(acquisitionYear) and isValidYear(aquisitionYearRangeEnd):
        acquisitionYear = aquisitionYearRangeEnd
        yearConfidence *= 0.5

    cleanedItems[i]["Acquisition Year"] = acquisitionYear
    cleanedItems[i]["Acquisition Year Confidence"] = yearConfidence
    cleanedItems[i]["Acquisition Era"] = str(acquisitionYear)[:2] + "00s"

    if len(acquisitionType) < 1:
        continue

    for find, replace in acquisitionTypeSynonyms:
        if acquisitionType == find:
            acquisitionType = replace
    cleanedItems[i]["Acquisition Type"] = acquisitionType.capitalize()
    cleanedItems[i]["Acquisition Type Confidence"] = typeConfidence

# Debugging...
# lu.countValues(cleanedItems, "Acquisition Year")
# lu.countValues(cleanedItems, "Acquisition Type")
# sys.exit()

##############################################
# STEP 2: retrieve country                   #
##############################################

# lu.countValues(items, "Country")

_, countrySynonyms = io.readCsv("data/usergen/CountriesSynonyms.csv")
countrySynonymLookup = lu.createLookup(countrySynonyms, "alt")
_, countryLatLons = io.readCsv("data/vendor/CountriesLatLon.csv")
countryLookup = lu.createLookup(countryLatLons, "name")

for i, item in enumerate(items):
    country = item["Country"].strip()
    countryConfidence = 1.0
    if len(country) < 1:
        continue

    # normalize lists
    country = country.replace("/", ", ")
    country = country.replace(" OR ", ", ")
    if "," in country:
        countryConfidence *= 0.5

    # check for question mark
    if "?" in country:
        country = country.split("?")[0].strip()
        countryConfidence *= 0.5

    # if list, take first
    if "," in country:
        country = country.split(",")[0]
        countryConfidence *= 0.5

    # check for parentheses
    country = country.strip("()")
    if "(" in country:
        country = country.split("(")[0]

    country = country.strip()
    country = country.title()

    if country in countrySynonymLookup:
        country = countrySynonymLookup[country]["name"]

    if country not in countryLookup:
        countryConfidence *= 0.5
    else:
        cleanedItems[i]["Latitude"] = countryLookup[country]["latitude"]
        cleanedItems[i]["Longitude"] = countryLookup[country]["longitude"]

    cleanedItems[i]["Country"] = country
    cleanedItems[i]["Country Confidence"] = countryConfidence

# Debugging...
# lu.countValues(cleanedItems, "Country")
# countries = lu.unique([item["Country"] for item in cleanedItems])
# for country in countries:
#     if country not in countryLookup:
#         print("Cannot find %s" % country)
# sys.exit()

##############################################
# STEP 3: retrieve hall                      #
##############################################

hallSynonyms = [
    ("Margaret Mead Hall Of Pacific Peoples", "Hall Of Pacific Peoples"),
    ("Gardner D. Stout Hall Of Asian Peoples", "Hall Of Asian Peoples"),
    ("Mexico And Central America Hall", "Hall Of Mexico And Central America")
]
for i, item in enumerate(items):
    if "Hall" not in item:
        continue

    hall = item["Hall"].strip().title()
    for find, replace in hallSynonyms:
        if hall == find:
            hall = replace
    cleanedItems[i]["Hall"] = hall
# Debugging...
# lu.countValues(cleanedItems, "Hall")
# sys.exit()

##############################################
# STEP 4: retrieve donor                     #
##############################################

donorLookup = {}
for i, item in enumerate(items):
    if "Donor" not in item:
        continue

    donor = item["Donor"].strip().title()

    # normalize donor names based on first two name parts
    parts = [part.strip() for part in donor.split(", ")]
    if len(parts) > 1:
        nameStart = ", ".join(parts[:2])
        items[i]["DonorNameStart"] = nameStart
        if nameStart not in donorLookup:
            donorLookup[nameStart] = donor

for i, item in enumerate(items):
    if "Donor" not in item:
        continue

    donorConfidence = 1.0
    donor = item["Donor"].strip().title()
    if "DonorNameStart" in item and item["DonorNameStart"] in donorLookup:
        donor = donorLookup[item["DonorNameStart"]]

    if "?" in donor:
        donor = donor.replace("?", "").strip()
        donorConfidence *= 0.5

    cleanedItems[i]["Donor"] = donor
    cleanedItems[i]["Donor Confidence"] = donorConfidence

# Debugging...
# lu.countValues(cleanedItems, "Donor")
# sys.exit()

io.writeCsv(a.OUTPUT_FILE, cleanedItems)
