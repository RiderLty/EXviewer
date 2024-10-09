import json
from os import times
import requests
try:
    remoteTranslation = requests.get(
        "https://github.com/EhTagTranslation/Database/releases/latest/download/db.text.json").json()
except Exception as e:
    print("Failed to download latest releases", e)
    exit(1)

outDict = {}

for item in remoteTranslation["data"]:
    tagtype = item["namespace"]
    outDict[tagtype] = {}
    for key in item["data"].keys():
        value = item["data"][key]["name"]
        outDict[tagtype][key] = value


with open(r"public/sources/translate.json",'w') as f:
    json.dump(  outDict,f, ensure_ascii=True)


print("Successfully write to file")
