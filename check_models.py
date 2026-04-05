import json, urllib.request;
try:
    data = json.load(urllib.request.urlopen('http://localhost:11434/api/tags'))
    for m in data['models']:
        print(f"{m['name']} - {m['size']}")
except Exception as e:
    print(e)
