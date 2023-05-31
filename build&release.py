import json
import requests
import os

if __name__ == "__main__":
    tag = input("tag:")
    title = input("title:")

    token = os.environ.get("EXVIEWER_GITHUB_ACTION_TOKEN")
    if not token :
        print("token error:",token)
        exit(1)
    header = {
        'Authorization': 'token '+token,
        "Accept": "application/vnd.github.everest-preview+json"
    }
    resp = requests.post(
        f'https://api.github.com/repos/DriverLin/EXviewer/dispatches',
        data=json.dumps({
            "event_type": "RELEASE",
            "client_payload": {
                "tag": tag,
                "title": f"{tag} : {title}"
            }
        }), headers=header, verify=False)
    print(resp.content)