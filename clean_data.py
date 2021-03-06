# -*- coding: utf-8 -*-

import argparse
import collections
from datetime import datetime
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
parser.add_argument('-in', dest="INPUT_FILE", default="data/MexicoAndCentralAmerica.csv", help="File generated by html_to_csv.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="data/processed/MexicoAndCentralAmerica_cleaned.csv", help="Output csv file")
a = parser.parse_args()

# Make sure output dirs exist
io.makeDirectories([a.OUTPUT_FILE])

fieldNames, items = io.readCsv(a.INPUT_FILE)
itemCount = len(items)

# this is where the clean data will go
cleanedItems = [{
    "Id": item["Catalog No"],
    "Acquisition Year": "",
    "Acquisition Type": "",
    "Latitude": 0,
    "Longitude": 0,
    "Country": "",
    "Locale": "",
    "Category": "",
    "Hall": ""
} for item in items]

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
datePattern = re.compile("([12][0-9]{3})(\-[12][0-9]{3})?( \[[A-Z, ]+\])?")

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
    # Check for year range
    aquisitionYearRangeEnd = ""
    if matches.group(2) is not None:
        aquisitionYearRangeEnd = int(matches.group(2).strip("-"))
    # Check for acquisition type
    acquisitionType = ""
    if matches.group(3) is not None:
        acquisitionType = matches.group(3).strip("[] ")
    # Check for a list; just take the first one
    if "," in acquisitionType:
        acquisitionType = acquisitionType.split(", ")[0]

    # Check for valid year range
    if isValidYear(acquisitionYear) and isValidYear(aquisitionYearRangeEnd):
        # Just take the mean
        acquisitionYear = int(round(0.5 * (acquisitionYear + aquisitionYearRangeEnd)))
    elif not isValidYear(acquisitionYear) and isValidYear(aquisitionYearRangeEnd):
        acquisitionYear = aquisitionYearRangeEnd

    cleanedItems[i]["Acquisition Year"] = acquisitionYear
    cleanedItems[i]["Acquisition Type"] = acquisitionType.capitalize()

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

for i, item in enumerate(items):
    country = item["Country"]
    if len(country) < 1:
        continue

    country = country.replace("?", "")
    country = country.replace("/", ", ")
    if "," in country:
        country = country.split(",")[0]
    country = country.strip()
    country = country.title()

    if country in countrySynonymLookup:
        country = countrySynonymLookup[country]["name"]

    cleanedItems[i]["Country"] = country

# Debugging...
# lu.countValues(cleanedItems, "Country")
# sys.exit()

##############################################
# STEP 3: retrieve lat lon                   #
##############################################

# Attempt to retrieve country lat lon
# Reference: https://developers.google.com/public-data/docs/canonical/countries_csv
_, countryLatLons = io.readCsv("data/vendor/CountriesLatLon.csv")
countryLatLonLookup = lu.createLookup(countryLatLons, "name")

# uCountries = lu.unique([item["Country"] for item in cleanedItems])
# for country in uCountries:
#     if len(country) < 1:
#         continue
#     if country not in countryLatLonLookup:
#         print("%s missing in country lat lon list" % country)
#         continue

for i, item in enumerate(cleanedItems):
    country = item["Country"]
    if country not in countryLatLonLookup:
        continue

    latlon = countryLatLonLookup[country]
    cleanedItems[i]["Latitude"] = latlon["latitude"]
    cleanedItems[i]["Longitude"] = latlon["longitude"]

##############################################
# STEP 4: retrieve locale                    #
##############################################

localeMap = {}
for i, item in enumerate(items):
    locale = item["Locale"].strip()
    country = item["Country"].strip()
    if len(locale) < 1:
        continue

    localeMap[item["Locale"]] = ""

    locale = locale.replace("?", "")
    locale = locale.replace("DF/", "")
    parts = locale.split(",")

    validParts = []
    for part in parts:
        part = part.strip()

        # remove anything in parentheses
        part = re.sub(r'\(.+\)', '', part)

        part = part.replace("/", ",")
        part = part.replace(";", ",")
        part = part.replace(" OR ", ",")
        part = part.replace("NEAR ", "")
        part = part.replace("VICINITY OF", "")
        part = part.replace("VICINITY", "")
        part = part.replace("NORTH OF", "")
        part = part.replace("SOUTH OF", "")
        part = part.replace("EAST OF", "")
        part = part.replace("SOUTH OF", "")
        part = part.replace("FOOT OF", "")

        if "," in part:
            part = part.split(",")[0]

        part = part.strip()

        # remove empty
        if len(part) < 1:
            continue

        # remove country
        if part == country:
            continue

        # remove anything with numbers
        if bool(re.search(r'\d', part)):
            continue

        # remove anything with keywords
        if bool(re.search(r'EXTENSION|TRENCH|TRAVERSE|PLATFORM|GROUP|SECTOR|HIGHWAY|EARLY|SURFACE|UPPER|LOWER|MOUND|SUN|RAILROAD|CHURCH|MUSEUM|FARM|NORTH SIDE|SOUTH SIDE|EAST SIDE|WEST SIDE', part)):
            continue

        # remove if too long
        if len(part) > 40:
            continue

        validParts.append(part)

    if len(validParts) < 1:
        continue

    locale = ", ".join(validParts)
    locale = locale.title()

    cleanedItems[i]["Locale"] = locale
    localeMap[item["Locale"]] = locale

# # debug
# values = [item["Locale"] for item in items]
# counter = collections.Counter(values)
# counts = counter.most_common()
# rows = []
# for value, count in counts:
#     if len(str(value).strip()) < 1:
#         continue
#     row = {}
#     row["Locale"] = value
#     row["Cleaned"] = localeMap[value]
#     row["Count"] = count
#     rows.append(row)
# io.writeCsv("data/localeDebug.csv", rows, ["Locale", "Cleaned", "Count"])
# sys.exit()

##############################################
# STEP 5: retrieve category                  #
##############################################

for i, item in enumerate(items):
    categories = item["Categories"].strip()
    category = item["Category"].strip()
    categories += "," + category

    categories = [c.strip() for c in categories.split(",")]
    categories = [c for c in categories if len(c) > 0]

    if len(categories) > 0:
        cleanedItems[i]["Category"] = categories[0].title()

##############################################
# STEP 6: retrieve hall                      #
##############################################

for i, item in enumerate(items):
    cleanedItems[i]["Hall"] = item["Hall"].strip().title()

fieldNames = [
    "Id",
    "Acquisition Year",
    "Acquisition Type",
    "Latitude",
    "Longitude",
    "Country",
    "Locale",
    "Category",
    "Hall"
]
io.writeCsv(a.OUTPUT_FILE, cleanedItems, fieldNames)
