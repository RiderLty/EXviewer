import asyncio
import json
import logging
import os
import ssl
from os.path import join as path_join
import threading
from time import perf_counter
import sys
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import FileResponse
from tinydb import TinyDB
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage
from uvicorn import Config, Server
from utils.BlockRules import getRulesChecker
from utils.HTMLParser import setParserUtcOffset
from utils.AioProxyAccessor import NOSQL_DBS, aoiAccessor, commentBody, downloadListBody
from utils.DBM import wsDBMBinder, EHDBM
from utils.tools import logger, makeTrackableException, printTrackableException, getUTCOffset
from utils.AutoTask import autoTask
import coloredlogs
from fastapi.middleware.cors import CORSMiddleware



serverLoop = asyncio.new_event_loop()
asyncio.set_event_loop(serverLoop)

ssl._create_default_https_context = ssl._create_unverified_context

if getattr(sys, 'frozen', False):  # 判断是否打为包
    ROOT_PATH = os.path.dirname(os.path.abspath(sys.executable))
    SERVER_FILE = path_join(sys._MEIPASS, "build")
elif __file__:
    ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
    SERVER_FILE = path_join(os.path.abspath(
        path_join(ROOT_PATH, r"..")), "build")
else:
    logger.error("FILE PATH UNKNOWN ERROR!")
CONFIG_PATH = path_join(ROOT_PATH, r"config.json")

if not os.path.exists(CONFIG_PATH):
    open(CONFIG_PATH, "w").write(json.dumps({
        "EH_DOWNLOAD_PATH": "",
        "EH_CACHE_PATH": "",
        "EH_DB_PATH": "",
        "EH_COOKIE": "",
        "UTC_OFFSET": "+08",
        "PORT": 7964,
        "API_BLOCK_RULE": {
            "TYPE": "BLACK_LIST",
            "WHITE_LIST": [],
            "BLACK_LIST": []
        }
    }, indent=4))
CONFIG = json.load(open(CONFIG_PATH))

checkBlock = getRulesChecker(CONFIG["API_BLOCK_RULE"])


def getConfig(key, default=None):  # 先检查环境变量 然后检查配置文件 如果default不空则返回default 否则报错
    if os.environ.get(key) != None:
        logger.info(f"config[{key}] from env", )
        return os.environ.get(key)
    if key in CONFIG and CONFIG[key] != "":
        logger.info(f"config[{key}] from config.json", )
        return CONFIG[key]
    if default != None:
        logger.info(f"config[{key}] using default : {default}")
        return default
    logger.error(f"config [{key}] not found !")
    sys.exit(1)


COOKIE = getConfig("EH_COOKIE", None)
DOWNLOAD_PATH = getConfig(
    "EH_DOWNLOAD_PATH", path_join(ROOT_PATH, r"download"))
CACHE_PATH = getConfig("EH_CACHE_PATH", path_join(ROOT_PATH, r"cache"))

GALLERY_PATH = path_join(DOWNLOAD_PATH, r"Gallery")
COVER_PATH = path_join(DOWNLOAD_PATH, r"cover")
DB_PATH = getConfig("EH_DB_PATH", path_join(DOWNLOAD_PATH, path_join("api", "NosqlDB.json")))

for pathName in [os.path.split(DB_PATH)[0], CACHE_PATH, GALLERY_PATH, COVER_PATH]:
    if not os.path.exists(pathName):
        os.makedirs(pathName)
        logger.info(f"创建了目录 {pathName}")

logger.info(f"画廊下载目录 {GALLERY_PATH}")
logger.info(f"封面下载目录 {COVER_PATH}")
logger.info(f"数据库文件 {DB_PATH}")
logger.info(f"缓存目录 {CACHE_PATH}")

FAVORITE_DISABLED = getConfig("EH_FAVORITE_DISABLED", 'false')
DOWNLOAD_DISABLED = getConfig("EH_DOWNLOAD_DISABLED", 'false')
EH_COMMENT_DISABLED = getConfig("EH_COMMENT_DISABLED", 'false')
EH_RATE_DISABLED = getConfig("EH_RATE_DISABLED", 'false')
PORT = int(getConfig("PORT", 7964))
UTC_OFFSET = int(getConfig("UTC_OFFSET", getUTCOffset())) * 3600
setParserUtcOffset(UTC_OFFSET)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    "Cookie": COOKIE,
}


class CachingMiddlewareAutoWrite(CachingMiddleware):
    def __init__(self, storage_cls, ttw=16):
        super().__init__(storage_cls)
        self.ttw = ttw
        self.running = True
        self.writeLock = threading.Lock()
        self.stopSignal = threading.Event()

    def write(self, data):
        with self.writeLock:
            self.cache = data
            self._cache_modified_count += 1

    def forceFlush(self):
        if self._cache_modified_count != 0:
            start = perf_counter()
            with self.writeLock:
                self.flush()
            logger.debug(
                f"write cache to file use {(perf_counter()-start) *1000:4f} ms")

    def writeWatcherThread(self):
        logger.info("CachingMiddlewareAutoWrite write thread start")
        while not self.stopSignal.wait(self.ttw):
            self.forceFlush()
        self.forceFlush()
        logger.info(f"CachingMiddlewareAutoWrite write thread stopped")

    def stop(self):
        self.stopSignal.set()


NOSQL_CACHE = CachingMiddlewareAutoWrite(JSONStorage)
NOSQL_DB = TinyDB(DB_PATH, storage=NOSQL_CACHE)
g_data_wsBinder = wsDBMBinder(NOSQL_DB.table('g_data'), serverLoop)
download_wsBinder = wsDBMBinder(NOSQL_DB.table('download'), serverLoop)
favorite_wsBinder = wsDBMBinder(NOSQL_DB.table('favorite'), serverLoop)
card_info_wsBinder = wsDBMBinder(NOSQL_DB.table('card_info'), serverLoop)
history_wsBinder = wsDBMBinder(NOSQL_DB.table('history'), serverLoop)

aioPa = aoiAccessor(
    headers=headers,
    coverPath=COVER_PATH,
    cachePath=CACHE_PATH,
    galleryPath=GALLERY_PATH,
    db=NOSQL_DBS(
        g_data_wsBinder.getDBM(),
        download_wsBinder.getDBM(),
        favorite_wsBinder.getDBM(),
        card_info_wsBinder.getDBM(),
        EHDBM(NOSQL_DB.table('father_tree'), serverLoop, None),
        history_wsBinder.getDBM()
    ),
    loop=serverLoop
)


app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/websocket/syncDict/g_data")
async def websocket_endpoint(websocket: WebSocket):
    await g_data_wsBinder.handel_connect(websocket)


@app.websocket("/websocket/syncDict/download")
async def websocket_endpoint(websocket: WebSocket):
    await download_wsBinder.handel_connect(websocket)


@app.websocket("/websocket/syncDict/favorite")
async def websocket_endpoint(websocket: WebSocket):
    await favorite_wsBinder.handel_connect(websocket)


@app.websocket("/websocket/syncDict/card_info")
async def websocket_endpoint(websocket: WebSocket):
    await card_info_wsBinder.handel_connect(websocket)

@app.websocket("/websocket/syncDict/history")
async def websocket_endpoint(websocket: WebSocket):
    await history_wsBinder.handel_connect(websocket)


@app.get("/api/addFavorite/{gid}/{token}/{index}")
async def addFavorite(request: Request, gid: int, token: str, index: int):
    if FAVORITE_DISABLED == "true":
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "FAVORITE_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    logger.info(f"添加收藏 {gid}_{token} {index}")
    try:
        await aioPa.addFavorite(gid, token, index)
        return {"msg": f"{gid}_{token}已添加到收藏夹{index}"}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 添加收藏失败")))


@app.get("/api/rmFavorite/{gid}/{token}")
async def rmFavorite(request: Request, gid: int, token: str):
    if FAVORITE_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "FAVORITE_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    logger.info(f"删除收藏 {gid}_{token}")
    try:
        await aioPa.rmFavorite(gid, token)
        return {"msg": f"{gid}_{token}已移除收藏"}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 移除收藏失败")))


@app.get("/api/download/{gid}/{token}")  # 添加单个下载
async def download(request: Request, gid: int, token: str):
    if DOWNLOAD_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "DOWNLOAD_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    logger.info(f"添加下载 {gid}_{token}")
    try:
        await aioPa.addDownload([[gid, token]])
        return {"msg": f"{gid}_{token}已添加到下载队列"}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 添加下载失败")))


@app.post("/api/download")  # 添加多个下载 顺序添加 最后的是最新的
async def listDownload(request: Request, gidList: downloadListBody):
    if DOWNLOAD_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "DOWNLOAD_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    logger.info(f"添加下载 {str(gidList.__root__)}")
    try:
        await aioPa.addListDownload(gidList.__root__)
        return {"msg": f"已添加 {len(gidList.__root__)}项下载"}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"添加下载失败")))


@app.get("/api/delete/{gid}/{token}")
async def delete(request: Request, gid: int, token: str):
    if DOWNLOAD_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "DOWNLOAD_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    logger.info(f"请求删除 {gid}_{token}")
    try:
        await aioPa.deleteDownload([[gid, token]])
        return {"msg": f"{gid}_{token}已删除"}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 删除失败")))


@app.get("/api/continueDownload")
async def continueDownload(request: Request,):
    if DOWNLOAD_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "DOWNLOAD_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    try:
        reDownloadCount = await aioPa.continueDownload()
        return {"msg": f"已开始{reDownloadCount}项下载"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, "continueDownload failed")))


@app.get("/api/Gallery/{gid_token}/{filename}")
async def getGalleryFile(gid_token: str, filename: str, cache="false", countOnly="false"):
    gid, token = gid_token.split("_")
    gid = int(gid)
    try:
        if filename == "g_data.json":
            return await aioPa.get_G_data(gid, token, (cache == "true"), (countOnly == "true"))
        elif filename == "gallery.pdf":
            # return 
            return Response(
            (await aioPa.makePDF(gid,token)).getvalue(),
            headers={"Content-Type": "application/pdf",
                     "Cache-Control": "max-age=31536000"},
        )
        else:
            index = int(filename.split(".")[0])
            return FileResponse(
                await aioPa.getGalleryImage(gid, token, index),
                headers={
                    "Content-Type": "image/jpeg",
                    "Cache-Control": "max-age=31536000",
                },
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=404, detail=str(
            makeTrackableException(e, f"请求文件 {gid_token}/{filename} 失败")))


@app.get("/api/preview/{gid}/{token}/{index}")
async def getPreviewBytes(gid: int, token: str, index: int):
    try:
        src = await aioPa.getGalleryPreview(gid, token, index)
        bytes = await aioPa.downloadImgBytes(src)
        return Response(
            bytes,
            headers={"Content-Type": "image/jpeg",
                     "Cache-Control": "max-age=31536000"},
        )
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"请求预览 {gid}/{token}/{index} 失败")))


@app.get("/api/comments/{gid}/{token}")
async def getComments(gid: int, token: str, fetchAll=None):
    try:
        return await aioPa.getComments(gid, token, fetchAll != None)
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"请求评论 {gid}/{token} 失败")))


@app.get("/api/list/{path}")
async def listMainGallery(path, request: Request):
    query = str(request.scope["query_string"], encoding="utf-8")
    url = path if query == "" else path + "?" + query
    try:
        return await aioPa.getMainPageGalleryCardInfo(f"https://exhentai.org/{url}")
    except Exception as e:
        trackE = makeTrackableException(e, f"请求列表 {url} 失败")
        printTrackableException(trackE)
        raise HTTPException(status_code=500, detail=str(trackE))


@app.get("/api/list/")
async def listMainGalleryNoPath(request: Request):
    query = str(request.scope["query_string"], encoding="utf-8")
    url = "" if query == "" else "?" + query
    try:
        return await aioPa.getMainPageGalleryCardInfo(f"https://exhentai.org/{url}")
    except Exception as e:
        trackE = makeTrackableException(e, f"请求列表 {url} 失败")
        printTrackableException(trackE)
        raise HTTPException(status_code=500, detail=str(trackE))


@app.get("/api/searchLocal/")
async def searchLocal(request: Request):
    query = str(request.scope["query_string"], encoding="utf-8")
    try:
        return aioPa.localSearch(query)
    except Exception as e:
        trackE = makeTrackableException(e, f"本地搜索 {query} 失败")
        printTrackableException(trackE)
        raise HTTPException(status_code=500, detail=str(trackE))


@app.get("/api/cover/{filename}")
async def asyncCover(filename: str):
    gid, token = filename.split(".")[0].split("_")
    gid = int(gid)
    try:
        return FileResponse(
            await aioPa.getGalleryCover(gid, token),
            headers={"Content-Type": "image/jpeg",
                     "Cache-Control": "max-age=31536000"},
        )
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=404, detail=str(
            makeTrackableException(e, f"请求封面 {filename} 失败")))


@app.get("/api/getDiskCacheSize")
def getDiskCacheSize():
    text = aioPa.getDiskCacheSize()
    return {"msg": text}


@app.get("/api/clearDiskCache")
def clearDiskCache():
    text = aioPa.clearDiskCache()
    return {"msg": text}


@app.get("/api/reUpdateLocalG_data/{count}")
def reUpdateLocalG_data(count: int):
    serverLoop.create_task(aioPa.reUpdateLocalG_data(count))
    return {"msg": "success"}


@app.get("/api/listAllDownload")
def apiListAllDownload():
    return aioPa.listAllDownload()


@app.websocket("/websocket/api/uploadZip")
async def handelUploadZipGallery(ws: WebSocket):
    try:
        await ws.accept()
        gid, token = (await ws.receive_text()).split("_")
        logger.info(f"从浏览器接收画廊中 {gid}_{token}.zip")
        bytes = await ws.receive_bytes()
        logger.info(f"接收bytes{len(bytes)}")
        await aioPa.addDownloadRecordFromZip(int(gid), token, bytes)
        await ws.close()
    except WebSocketDisconnect as e:
        print("ws 断开", e)
        pass


@app.websocket("/websocket/api/syncFromOtherServer")
async def handelSyncFromOtherServer(ws: WebSocket):
    try:
        await ws.accept()
        await aioPa.syncFromOtherServer(ws.send_text, ws.receive_text)
        await ws.close()
    except WebSocketDisconnect as e:
        pass


@app.get("/api/rateGallery/{gid}/{token}/{score}")
async def rateGallery(request: Request, gid: int, token: str, score: float):
    if EH_RATE_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "EH_RATE_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    try:
        return await aioPa.rateGallery(gid, token, score)
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 评分失败")))


@app.get("/api/voteComment/{gid}/{token}/{commentId}/{vote}")
async def voteComment(request: Request, gid: int, token: str, commentId: int, vote: int):
    if EH_COMMENT_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "EH_COMMENT_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    try:
        return await aioPa.voteComment(gid, token, commentId, vote)
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{gid}_{token} 投票失败")))


@app.post("/api/postComment")
async def postComment(request: Request, comment: commentBody):
    if EH_COMMENT_DISABLED == "true":
        raise HTTPException(
            status_code=403, detail=str(makeTrackableException(None, "EH_COMMENT_DISABLED,该API已禁用")))
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    try:
        return await aioPa.postComment(comment)
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"{comment.gid}_{comment.token} 评论失败")))


@app.get("/api/deleteOldGallery")
async def deleteOldGallery():
    try:
        return {"msg": await aioPa.deleteOldGallery()}
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"删除任务失败")))


@app.get("/api/history/list")
async def geHistory(request: Request, next: int = None):
    return aioPa.getHistory()


@app.get("/api/history/add")
async def addHistory(request: Request, gid: int, token: str):
    await aioPa.addHistory(gid, token)
    return {"msg": "success"}


@app.get("/api/history/clear")
async def clearHistory():
    return {"msg": aioPa.clearHistory()}


@app.get("/")
def index():
    return FileResponse(path_join(SERVER_FILE, "index.html"))


app.mount("/", StaticFiles(directory=SERVER_FILE), name="static")


def init_logger():
    LOGGER_NAMES = ("uvicorn", "uvicorn.access",)
    for logger_name in LOGGER_NAMES:
        logging_logger = logging.getLogger(logger_name)
        fmt = f"🌏 %(asctime)s.%(msecs)03d .%(levelname)s \t%(message)s"  # 📨
        coloredlogs.install(
            level=logging.DEBUG, logger=logging_logger, milliseconds=True, datefmt="%X", fmt=fmt
        )


def getServer(port):
    serverConfig = Config(
        app=app,
        # host="::",
        host="0.0.0.0",
        port=port,
        log_level="info",
        loop=serverLoop,
        ws_max_size=1024*1024*1024*1024,
    )
    return Server(serverConfig)
autoTaskInstance = autoTask(loop=serverLoop,aioPa=aioPa)

if __name__ == "__main__":
    serverInstance = getServer(PORT)
    init_logger()
    DB_CACHE_WRITER = threading.Thread(target=NOSQL_CACHE.writeWatcherThread)
    DB_CACHE_WRITER.start()
    # autoTaskInstance.start()
    serverLoop.run_until_complete(serverInstance.serve())
    # autoTaskInstance.stop()
    NOSQL_CACHE.stop()
    DB_CACHE_WRITER.join()
