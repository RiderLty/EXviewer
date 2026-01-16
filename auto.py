import requests
import json

mustTags = {}
blockTags = {
    "female:mother",
    "female:double vaginal",
    "female:double anal",
    "female:moral degeneration",
    "female:piercing",
    "female:large tattoo",
    "male:males only",
    "male:yaoi",
    "female:big areolae",
    "female:huge breasts",
    "female:fisting",
    "male:human on furry",
    "male:furry",
    "female:furry",
    "female:nipple fuck",
    "female:ryona",
    "female:torture",
    "male:dickgirl on male",
    "female:scat",
    "female:farting",
    "male:scat",
    "female:netorase",
    "female:insect"
}
favIndex = 5

HOST = "http://192.168.3.3:7965"

def filter(g_data):
    if "tags" not in g_data.keys():
        return False 
    for tag in g_data["tags"]:
        if tag in mustTags:
            return True
    for tag in g_data["tags"]:
        if tag in blockTags:
            return False

    if "language:chinese" not in g_data["tags"]:
        return False

    if float(g_data["rating"]) < 3.8:
        return False

    if int(g_data["filecount"]) > 300:
        return False

    if g_data["category"] not in ["Manga", "Doujinshi"]:
        return False
    # print(json.dumps(g_data, indent=4, ensure_ascii=False))
    return True


downloaded = requests.get(f"{HOST}/api/listAllDownload").json()
# for item in sorted(downloaded.values() , key= lambda x: x["index"],reverse=True):
for item in sorted(downloaded.values() , key= lambda x: x["index"],reverse=True)[:200]:
    gid = item["gid"]
    token = item["token"]
    g_data = requests.get(f"{HOST}/api/Gallery/{gid}_{token}/g_data.json?cache=true").json()
    if not filter(g_data):
        print(g_data)
        print(requests.get(f"{HOST}/api/delete/{gid}/{token}").text)
        print("\n")


requests.get(f"{HOST}/api/continueDownload")
requests.get(f"{HOST}/api/reUpdateLocalG_data/100")
res = requests.get(f"{HOST}/api/list/popular").json()
gidList = [[x["gid"], x["token"]] for x in res]
res = requests.post(f"{HOST}/api/fetch_g_data", data=json.dumps(gidList)).json()
download = [(x["gid"], x["token"]) for x in res if filter(x)]
res = requests.post(f"{HOST}/api/download", data=json.dumps(download)).json()
print(res)
for gid, token in download:
    requests.get(f"{HOST}/api/addFavorite/{gid}/{token}/{favIndex}")
