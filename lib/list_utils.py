import collections
import itertools
from operator import itemgetter
import lib.math_utils as mu

def countValues(arr, key, displayCount=-1, printLines=True):
    values = [item[key] if item[key] != "" else "<empty>" for item in arr]
    itemCount = len(arr)
    uvalues = unique(values)

    outputLines = ["\n=============================================================================="]
    outputLines.append("Field: %s (%s unique values):" % (key, mu.formatNumber(len(uvalues))))
    outputLines.append("------------------------------------------------------------------------------")

    counter = collections.Counter(values)
    counts = counter.most_common(displayCount) if displayCount > 0 else counter.most_common()
    for value, count in counts:
        outputLines.append("%s (%s%%)\t %s" % (mu.formatNumber(count), round(1.0 * count / itemCount * 100.0, 2), value))

    if printLines:
        for line in outputLines:
            print(line)

    return outputLines

def createLookup(arr, key):
    return dict([(str(item[key]), item) for item in arr])

def flattenList(arr):
    return [item for sublist in arr for item in sublist]

def groupList(arr, groupBy, sort=False, desc=True):
    groups = []
    arr = sorted(arr, key=itemgetter(groupBy))
    for key, items in itertools.groupby(arr, key=itemgetter(groupBy)):
        group = {}
        litems = list(items)
        count = len(litems)
        group[groupBy] = key
        group["items"] = litems
        group["count"] = count
        groups.append(group)
    if sort:
        reversed = desc
        groups = sorted(groups, key=lambda k: k["count"], reverse=reversed)
    return groups

def unique(arr):
    return list(set(arr))
