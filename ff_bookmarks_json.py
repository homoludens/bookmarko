import json

def load_bookmarks_file(filename):
    with open(filename) as json_data:
        return json.load(json_data)
        

def flatten(bookmarks):
    result = []
    if bookmarks != None:
        for bookmark in bookmarks:
            result.append(bookmark)
            if bookmark.get("type") == "text/x-moz-place-container":
                children_bookmarks = flatten(bookmark.get("children"))
                for child in children_bookmarks:
                    result.append(child)
    return result

def flatten_bookmarks(bookmarks):
    return [b for b in flatten(bookmarks) if b.get("type") == "text/x-moz-place"]

def flatten_directories(bookmarks):
    return [b for b in flatten(bookmarks) if b.get("type") == "text/x-moz-place-container"]



bookmarks = load_bookmarks_file('/home/homoludens/Desktop/Old Firefox Data/bookmarks-2020-10-19.json')
