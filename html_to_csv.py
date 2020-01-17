# -*- coding: utf-8 -*-

# Usage:
#   The following gets results from Donor "Lumholtz", on display, Mexico and Central America collection, ethnographic type, country Mexico
#     python3 scrape_html.py -query "object_list=Lumholtz&search_list=dn&on_display=on&coll_id=4&type_base=E&country_list=MEXICO"

import argparse
from bs4 import BeautifulSoup
import math
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import sys

import lib.io_utils as io
import lib.list_utils as lu

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="downloads/MexicoAndCentralAmerica/page-*.html", help="Input file pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="data/MexicoAndCentralAmerica.csv", help="Output csv file")
parser.add_argument('-threads', dest="THREADS", default=4, type=int, help="Number of concurrent threads, -1 for all available")
a = parser.parse_args()

fieldNames = []

# Make sure output dirs exist
io.makeDirectories([a.OUTPUT_FILE])
filenames = io.getFilenames(a.INPUT_FILE)

def parseHTMLFile(fn):
    contents = ""
    with open(fn, "r") as f:
        contents = f.read()

    print("Parsing %s..." % fn)
    bs = BeautifulSoup(contents, "html.parser")
    theForm = bs.find("form", {"name": "HiddenForm1"})
    results = theForm.find_all("table", {"cellpadding": "4"})
    items = []

    for row in results:
        fields = row.find_all("div", {"class": "div_bottom3"})
        item = {}

        for index, field in enumerate(fields):
            fieldName = ""
            fieldText = ""
            if index == 0:
                fieldName = "Title"
                fieldText = field.find("div", {"class": "object_title"}).find("b").string.strip()
            elif index == 1:
                fieldName = "Collection"
                fieldText = field.string.strip()
            else:
                fieldName = field.find("b")
                if fieldName is None:
                    continue

                fieldName = fieldName.string.strip()
                fieldText = ""

                if fieldName.endswith(":"):
                    fieldName = fieldName.rstrip(":")
                    if field.find("a") is not None:
                        fieldText = field.find("a").string.strip()
                    elif field.find("span") is not None:
                        fieldText = field.find("span").string.strip()
                    else:
                        fieldText = field.contents[-1].strip()
                else:
                    fieldContent = field.parent.find("div", {"class": "div_indent"})
                    if fieldContent is not None:
                        fieldText = fieldContent.get_text().strip()

            item[fieldName] = fieldText

        image = row.find("img", {"border": "1"})
        if image is not None:
            item["Thumb URL"] = image.get("src")

        notes = row.find("span", {"class": "note_text"})
        if notes is not None and notes.string is not None:
            item["Curatorial Notes"] = notes.string.strip()

        hall = row.find("img", {"title": "On Permanent Exhibit in AMNH Hall"})
        if hall is not None:
            item["Hall"] = hall.parent.contents[-1].strip()

        items.append(item)
    return items

pool = ThreadPool(a.THREADS)
results = pool.map(parseHTMLFile, filenames)
pool.close()
pool.join()

items = lu.flattenList(results)

fieldNames = set([])
for item in items:
    fieldNames = fieldNames.union(set([key for key in item]))
fieldNames = list(fieldNames)
fieldNames = sorted(fieldNames)

items = sorted(items, key=lambda item: item['Catalog No'])

io.writeCsv(a.OUTPUT_FILE, items, fieldNames)
