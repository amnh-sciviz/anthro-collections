# -*- coding: utf-8 -*-

# Usage:
#   The following gets results from Donor "Lumholtz", on display, Mexico and Central America collection, ethnographic type, country Mexico
#     python3 scrape_html.py -query "object_list=Lumholtz&search_list=dn&on_display=on&coll_id=4&type_base=E&country_list=MEXICO"

import argparse
from bs4 import BeautifulSoup
import math
import os
from pprint import pprint
import sys
from urllib.parse import urlparse

import lib.io_utils as io

# input
parser = argparse.ArgumentParser()
parser.add_argument('-url', dest="URL", default="https://anthro.amnh.org/anthropology/databases/common/query_result.cfm", help="Form URL")
parser.add_argument('-query', dest="QUERY", default="coll_id=4", help="Query string")
parser.add_argument('-dir', dest="HTML_DIR", default="downloads/MexicoAndCentralAmerica/page-%s.html", help="Directory to store raw html data")
parser.add_argument('-pp', dest="PER_PAGE", default=200, type=int, help="Number of records per page")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
a = parser.parse_args()

query = {
    "search_list": "nm",
    "object_list": "",
    "coll_id": "-ALL-",
    "type_base": "-ALL-",
    "categories": "",
    "current_view": "fm",
    "imaged": "",
    "rec_per_page": a.PER_PAGE
}
inputQuery = io.parseQueryString(a.QUERY)
query.update(inputQuery)

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    # "Content-Length": "123",
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": "anthro.amnh.org",
    "Origin": "https://anthro.amnh.org",
    "Referer": "https://anthro.amnh.org/anthropology/databases/common/query_categories.cfm?",
    "Sec-Fetch-Mode": "nested-navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
}

# Make sure output dirs exist
io.makeDirectories([a.HTML_DIR])

if a.OVERWRITE:
    io.removeFiles(a.HTML_DIR % '*')

page = 1
zeroPadding = 4
perPage = query["rec_per_page"]
totalPages = None
totalRecords = None
currentRecord = None
prevPageQuery = None
while True:

    postData = query.copy() if prevPageQuery is None else prevPageQuery
    filename = a.HTML_DIR % str(page).zfill(zeroPadding)

    if totalPages is not None and page > totalPages:
        break

    html = io.downloadFile(a.URL, postData, filename, headers, overwrite=a.OVERWRITE)
    # print(html)
    # break
    bs = BeautifulSoup(html, "html.parser")
    inputs = bs.find_all("input", {"type": "hidden"}) + bs.find_all("input", {"type": "text"}) + bs.find_all("select")

    prevPageQuery = {}
    for input in inputs:
        value = ""
        if input.name == "select":
            options = input.find_all("option")
            value = options[0].get("value")
            for option in options:
                if option.has_attr("selected"):
                    value = option.get("value")
                    break
        else:
            value = input.get("value")
        prevPageQuery[input.get("name")] = value if value is not None else ""

    if totalRecords is None:
        # Retrieve total records, e.g. <input type="hidden" name="total_records" value="5597">
        totalRecords = int(prevPageQuery["total_records"])
        totalPages = int(math.ceil(1.0 * totalRecords / perPage))
        print("%s records found over %s pages" % (totalRecords, totalPages))

    page += 1
    currentRecord = (page - 1) * perPage + 1
    prevPageQuery["current_record"] = currentRecord
    prevPageQuery["total_records"] = totalRecords

    # pprint(prevPageQuery)
    # break
    # if page > 2:
    #     break
