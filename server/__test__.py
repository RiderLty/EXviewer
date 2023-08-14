import asyncio
import json
import os
import ssl
from os.path import join as path_join
import sys
import threading
from time import perf_counter

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
from utils.AioProxyAccessor import NOSQL_DBS, aoiAccessor, commentBody
from utils.DBM import wsDBMBinder,EHDBM
from utils.tools import logger, makeTrackableException, printTrackableException, getUTCOffset
from fastapi.middleware.cors import CORSMiddleware

serverLoop = asyncio.new_event_loop()
asyncio.set_event_loop(serverLoop)

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
DB_PATH = path_join(DOWNLOAD_PATH, path_join("api", "NosqlDB.json"))

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


async def test():
    res = await aioPa.getMainPageGalleryCardInfo("https://exhentai.org/")
    print(res)


if __name__ == "__main__":
    print("running")
    DB_CACHE_WRITER = threading.Thread(target=NOSQL_CACHE.writeWatcherThread)
    DB_CACHE_WRITER.start()
    logger.debug("test start ")
    serverLoop.run_until_complete(test())
    logger.debug("test over ")
    NOSQL_CACHE.stop()
    DB_CACHE_WRITER.join()
