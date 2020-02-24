# -*- coding: utf-8 -*-

import argparse
import bz2
import math
import numpy as np
import os
import pickle
from PIL import Image, ImageDraw, ImageFont
from pprint import pprint
import sys

import lib.io_utils as io
import lib.list_utils as lu
import lib.math_utils as mu

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="data/processed/all_normalized.csv", help="File generated by normalize_data.py")
parser.add_argument('-margin', dest="MARGIN", default=20, type=int, help="Base margin in px")
parser.add_argument('-itemwidth', dest="ITEM_WIDTH", default=16, type=int, help="Item width in px")
parser.add_argument('-ipc', dest="ITEMS_PER_COLUMN", default=10, type=int, help="Items per column")
parser.add_argument('-fontsize', dest="FONT_SIZE", default=20, type=int, help="Base font size in pixels")
parser.add_argument('-xaxis', dest="X_AXIS", default="Acquisition Year", help="Output image filename")
parser.add_argument('-yaxis', dest="Y_AXIS", default="Region", help="Output image filename")
parser.add_argument('-img', dest="IMAGE_FILE", default="images/{Region}/{Filename}", help="Input image file pattern")
parser.add_argument('-cache', dest="CACHE_FILE", default="tmp/imageCache_16.p.gz", help="Input image file pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="data/viz/timeline%s.jpg", help="Output image filename")
parser.add_argument('-count', dest="IMAGE_COUNT", default=4, type=int, help="Number of images to produce")
parser.add_argument('-height', dest="IMAGE_HEIGHT", default=2160, type=int, help="Target height")
parser.add_argument('-ywidth', dest="YEAR_WIDTH", default=100, type=int, help="Target height")
parser.add_argument('-gwidth', dest="ITEM_GROUP_WIDTH", default=4.0, type=float, help="Max width of the an item group as a percentage of min(year width, region height)")
parser.add_argument('-plot', dest="PLOT", action="store_true", help="Plot the data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output details?")
a = parser.parse_args()

COLORS = ["#612323", "#204f1c", "#4d1e59", "#112e6b", "#4b5713", "#571330"]
colorCount = len(COLORS)

# Make sure output dirs exist
io.makeDirectories([a.OUTPUT_FILE, a.CACHE_FILE])
font = ImageFont.truetype(font="fonts/Open_Sans/OpenSans-Regular.ttf", size=a.FONT_SIZE)

print("Reading data...")
fieldNames, items = io.readCsv(a.INPUT_FILE)

yLabels = lu.unique([item[a.Y_AXIS] for item in items])
if a.Y_AXIS == "Region":
    items = [item for item in items if item["Region"] != "Europe"]
    itemsByRegion = lu.groupList(items, "Region")
    for i, region in enumerate(itemsByRegion):
        itemsByRegion[i]["lat"] = np.mean([item["Latitude"] for item in region["items"] if -90 <= item["Latitude"] <= 90])
    itemsByRegion = sorted(itemsByRegion, key=lambda region: -region["lat"])
    yLabels = [region["Region"] for region in itemsByRegion]
else:
    yLabels = sorted(yLabels)
yLabelCount = len(yLabels)

xLabels = []
yearStart = yearEnd = None
if "Year" in a.X_AXIS:
    items = [item for item in items if item[a.X_AXIS] < 9999]
    items = sorted(items, key=lambda item: item[a.X_AXIS])
    yearStart = items[0][a.X_AXIS]
    yearEnd = items[-1][a.X_AXIS]
    print("Year range: %s - %s" % (yearStart, yearEnd))
    for i in range(yearEnd-yearStart+1):
        xLabels.append(yearStart+i)
else:
    xLabels = lu.unique([item[a.X_AXIS] for item in items])
    xLabels = sorted(xLabels)
xLabelCount = len(xLabels)

# itemTest = [item for item in items if item[a.X_AXIS] > 2000]
# pprint(itemTest)
# sys.exit()

# pprint(xLabels)
# pprint(yLabels)

itemCount = len(items)
for i, item in enumerate(items):
    items[i]["index"] = i

# First group by X
groupedItems = lu.groupList(items, a.X_AXIS)

# Then by Y
maxGroupItemCount = 0
for i, xgroup in enumerate(groupedItems):
    ygroups = lu.groupList(xgroup["items"], a.Y_AXIS)
    maxGroupItemCount = max(maxGroupItemCount, max(group["count"] for group in ygroups))
    groupedItems[i]["items"] = lu.createLookup(ygroups, a.Y_AXIS)

# Debug with matplotlib
if a.PLOT:
    import matplotlib.pyplot as plt
    yGroups = [[0]*xLabelCount for ygroup in yLabels]
    for i, xgroup in enumerate(groupedItems):
        for j, yLabel in enumerate(yLabels):
            count = 0
            if yLabel in xgroup["items"]:
                count = len(xgroup["items"][yLabel]["items"])
            yGroups[j][i] = count
    bars = []
    for i, yGroup in enumerate(yGroups):
        bar = None
        if i > 0:
            bar = plt.bar(xLabels, yGroup, bottom=yGroups[i-1])
        else:
            bar = plt.bar(xLabels, yGroup)
        bars.append(bar)
    plt.xlabel('Year')
    plt.ylabel('Region')
    plt.legend(tuple([bar[0] for bar in bars]), tuple(yLabels))
    plt.show()
    sys.exit()

# Load image data from cache file if it exists
imageData = None
if not a.PROBE and os.path.isfile(a.CACHE_FILE):
    print("Reading cache file...")
    with bz2.open(a.CACHE_FILE, "rb") as f:
        imageData = pickle.load(f)
        print("Loaded image data from %s" % a.CACHE_FILE)
        # imTest = Image.fromarray(imageData[0], mode="RGB")
        # imTest.show()
        # sys.exit()
        _itemCount, _itemW, _itemH, _rgb = imageData.shape
        if _itemCount != itemCount or _itemW != a.ITEM_WIDTH:
            imageData = None
            print("Pixel size mismatch: Found (%s, %s, %s), expected (%s, %s, %s)" % (_itemCount, _itemW, _itemH, itemCount, a.ITEM_WIDTH, a.ITEM_WIDTH))
            print("Delete cache file (%s) or input a new one" % a.CACHE_FILE)
            sys.exit()

# Otherwise rebuild cache
if not a.PROBE and imageData is None:
    noIm = Image.open("images/no_image.jpg")
    noIm.thumbnail((a.ITEM_WIDTH, a.ITEM_WIDTH), resample=Image.LANCZOS)
    imageData = np.zeros((itemCount, a.ITEM_WIDTH, a.ITEM_WIDTH, 3), dtype=np.uint8)
    print("Building cache...")
    for i, item in enumerate(items):
        itemCopy = item.copy()
        itemCopy["Region"] = itemCopy["Region"].replace(" ", "")
        filename = a.IMAGE_FILE.format(**itemCopy)
        im = False

        if os.path.isfile(filename):
            try:
                im = Image.open(filename)
                im = im.convert("RGB")
                im.thumbnail((a.ITEM_WIDTH, a.ITEM_WIDTH), resample=Image.LANCZOS)
            except OSError:
                print("Image file error with %s" % filename)
                im = False
        else:
            print("Could not find image %s" % filename)

        if im is False:
            im = noIm

        tpixels = np.array(im)
        tw, th = im.size
        tx = ty = 0
        if tw > th:
            ty = int((a.ITEM_WIDTH-th) * 0.5)
        else:
            tx = int((a.ITEM_WIDTH-tw) * 0.5)

        imageData[i, ty:ty+th, tx:tx+tw] = tpixels
        # imTest = Image.fromarray(imageData[i], mode="RGB")
        # imTest.show()
        # sys.exit()

        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(i+1)/itemCount*100,2))
        sys.stdout.flush()
    print("Compressing and saving cache...")
    pickle.dump(imageData, bz2.open(a.CACHE_FILE, 'wb'))

annotationsHeight = 480 - a.MARGIN
totalW = xLabelCount * a.YEAR_WIDTH + a.MARGIN * 2
imageH = a.IMAGE_HEIGHT
itemsHeight = imageH - annotationsHeight - a.MARGIN
imageW = int(totalW / a.IMAGE_COUNT)
print("Image dimensions: (%spx x %spx)" % (imageW, imageH))
if a.PROBE:
    sys.exit()

# Calculate positioning
itemsGroupHeight = itemsHeight/yLabelCount
maxItemGroupWidth = min(a.YEAR_WIDTH, itemsGroupHeight) * a.ITEM_GROUP_WIDTH
itemsMargin = int(round((maxItemGroupWidth - itemsGroupHeight) * 0.5))
itemsGroupHeight = int(round(1.0 * (itemsHeight-itemsMargin*2) / yLabelCount))
for i, groupx in enumerate(groupedItems):
    index = i
    if yearStart is not None:
        index = groupx[a.X_AXIS] - yearStart
    x0 = a.MARGIN + index * a.YEAR_WIDTH # the x value of the group
    xc = x0 + a.YEAR_WIDTH * 0.5
    for j, labelY in enumerate(yLabels):
        y0 = itemsMargin + j * itemsGroupHeight
        yc = y0 + itemsGroupHeight * 0.5

        if labelY not in groupx["items"]:
            continue

        groupItems = groupx["items"][labelY]["items"]
        groupCount = len(groupItems)
        ncount = 1.0 * groupCount / maxGroupItemCount
        nradius = max(math.sqrt(ncount), 0.1)
        groupRadius = maxItemGroupWidth * 0.5 * nradius

        for k, item in enumerate(groupItems):
            itemX, itemY = mu.randomPointInCircle(xc, yc, groupRadius)
            groupedItems[i]["items"][labelY]["items"][k]["x"] = itemX - (a.ITEM_WIDTH*0.5)
            groupedItems[i]["items"][labelY]["items"][k]["y"] = itemY - (a.ITEM_WIDTH*0.5)

im = Image.new('RGB', (totalW, imageH), (0,0,0))
draw = ImageDraw.Draw(im)

# draw y axis background colors
for i, ylabel in enumerate(yLabels):
    color = COLORS[i % colorCount]
    y = itemsMargin + i * itemsGroupHeight
    draw.rectangle([(0, y), (totalW, y+itemsGroupHeight)], fill=color)

# draw x axis labels
for i, xlabel in enumerate(xLabels):
    xlabel = str(xlabel)
    x0 = a.MARGIN + i * a.YEAR_WIDTH
    xc = x0 + a.YEAR_WIDTH * 0.5
    y0 = itemsHeight
    yc = itemsHeight + a.MARGIN * 0.5
    tw, th = font.getsize(xlabel)
    x = xc - tw * 0.5
    y = yc - th * 0.5
    draw.text((int(x), int(y)), xlabel, font=font, fill=(255,255,255))

# draw y axis labels
displayCount = 10
displayWidth = totalW / (displayCount+1)
for i, ylabel in enumerate(yLabels):
    y = itemsMargin + i * itemsGroupHeight + 2
    for j in range(displayCount):
        x = a.MARGIN + j * displayWidth
        draw.text((int(x), int(y)), ylabel, font=font, fill=(255,255,255))

# draw central timeline

# draw items
print("Adding items to image...")
progress = 0
for i, groupx in enumerate(groupedItems):
    for labelY in groupx["items"]:
        for k, item in enumerate(groupx["items"][labelY]["items"]):
            itemPixels = imageData[item["index"]]
            itemImg = Image.fromarray(itemPixels, mode="RGB")
            im.paste(itemImg, (int(item["x"]), int(item["y"])))

            progress += 1
            sys.stdout.write('\r')
            sys.stdout.write("%s%%" % round(1.0*progress/itemCount*100,2))
            sys.stdout.flush()

print("Saving each image...")
for i in range(a.IMAGE_COUNT):
    fn = a.OUTPUT_FILE % i
    (left, upper, right, lower) = (i*imageW, 0, (i+1)*imageW, imageH)
    imPart = im.crop((left, upper, right, lower))
    imPart.save(fn)
    print("Saved %s" % fn)
