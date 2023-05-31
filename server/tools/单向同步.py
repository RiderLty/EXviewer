import json
import os
from urllib.parse import urljoin
import websockets
import asyncio
from PIL import Image
from aiohttp import ClientSession, ClientTimeout
import shutil

HOST = "http://192.168.3.64:7964"
GALLERY_PATH = r"D:\EHDownloads\Gallery"


DOWNLOAD_WS_URL = HOST.replace(
    "http://", "ws://").replace("https://", "wss://") + "/websocket/syncDict/download"
CARD_WS_URL = HOST.replace(
    "http://", "ws://").replace("https://", "wss://") + "/websocket/syncDict/card_info"


def get_path(gid: int, token: str, index: int) -> str:
    galleryDir = os.path.join(GALLERY_PATH, f"{gid}_{token}")
    if not os.path.exists(galleryDir):
        os.makedirs(galleryDir)
    return os.path.join(galleryDir, f"{index:08d}.jpg")


def get_url(gid: int, token: str, index: int) -> str:
    return urljoin(HOST, f"/api/Gallery/{gid}_{token}/{index:08d}.jpg")


def check_img(abs_path):
    if abs_path == None:
        return False
    if not os.path.exists(abs_path):
        return False
    else:
        try:
            Image.open(abs_path).verify()
            return True
        except Exception as e:
            print(f"{abs_path} verify failed: {e}")
            if os.path.exists(abs_path):
                os.remove(abs_path)
            return False


async def read_ws(url):
    print(f"reading from {url}")
    async with websockets.connect(
        url,
        max_size=1024*1024*1024*1024
    ) as websocket:
        await websocket.send("sync")
        res = await websocket.recv()
        await websocket.close()
        print("read success")
        return res


async def main():
    local = json.loads(await read_ws("ws://127.0.0.1:7964/websocket/syncDict/download"))["data"]
    remote = json.loads(await read_ws(DOWNLOAD_WS_URL))["data"]
    
    card = json.loads(await read_ws(CARD_WS_URL))["data"]
    
    gid_list = []
    
    for remote_gid in remote.keys():
        # if remote_gid not in local:  #即使已经下载check一遍 避免手动下载时顺序错乱
        gid_list.append(remote_gid)
    
    targets = sorted([remote[x] for x in gid_list],
                     key=lambda x: x["index"], reverse=False)
    
    needDownloadList = [[int(x["gid"]), x["token"]] for x in targets]  #最早的在最前面 添加的时候，从前向后添加下载 可保证同样的下载index顺序
    
    # needDownloadList = needDownloadList
    #分段需要注意顺序 
    #想要保持相同的顺序，则需要 [-500:-200] , [-200:-100] , [-100:] 这样去下
    
    print("needDownloadList",needDownloadList)

    print("下载数", len(needDownloadList))
    
    downloadTaskQueue = asyncio.Queue()
    downloadSemaphore = asyncio.Semaphore(3)
    taskCount = 0
    
    for (gid, token) in needDownloadList:
        assert str(gid) in card
        for i in range(card[str(gid)]["pages"]):
            await downloadTaskQueue.put((gid, token, i+1))
            taskCount += 1

    session = ClientSession()

    async def func():
        async with downloadSemaphore:
            (gid, token, index) = await downloadTaskQueue.get()
            if check_img(get_path(gid, token, index)):
                print("\r", get_path(gid, token, index), "pass", end=" ")
            else:
                try:
                    res = await session.get(get_url(gid, token, index))
                    bytes = await res.read()
                    with open(get_path(gid, token, index), 'wb') as f:
                        f.write(bytes)
                    check_img(get_path(gid, token, index))
                    print("\r", (gid, token, index), len(bytes), end=" ")
                except Exception as e:
                    print("\r", (gid, token, index), e, end=" ")
            restLength = 40 * downloadTaskQueue.qsize() // taskCount
            print("\t" + "o" * (40-restLength) + "-" * restLength)

    tasks = [asyncio.create_task(func()) for i in range(taskCount)]

    await asyncio.gather(*tasks)

    resp = await session.post(
        url="http://127.0.0.1:7964/api/download",
        json=needDownloadList,
    )
    print(await resp.json())
    if input("保留最近20?\t0=YES") == "0":
        print("删除中")
        for download in remote.values()[:-20]:
            resp = await session.get(f"{HOST}/api/delete/{download['gid']}/{download['token']}")
            print(f"{download['gid']}/{download['token']}", await resp.text())

    await session.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
