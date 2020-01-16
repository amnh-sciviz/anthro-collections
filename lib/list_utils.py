def createLookup(arr, key):
    return dict([(str(item[key]), item) for item in arr])

def flattenList(arr):
    return [item for sublist in arr for item in sublist]
