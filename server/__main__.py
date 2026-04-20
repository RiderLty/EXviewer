import asyncio
import json
import logging
import os
import ssl
import zlib
from os.path import join as path_join
import threading
from time import perf_counter
import sys
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import FileResponse, StreamingResponse
from tinydb import TinyDB
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage
from uvicorn import Config, Server
from utils.BlockRules import getRulesChecker
from utils.HTMLParser import setParserUtcOffset
from utils.AioProxyAccessor import NOSQL_DBS, aoiAccessor, commentBody, downloadListBody, gidTokenListBody
from utils.DBM import EHDBM, SSEDBMBinder, DOWNLOAD_STATE, FAVORITE_STATE, LOAD
from utils.tools import logger, makeTrackableException, printTrackableException, getUTCOffset
from utils.AutoTask import autoTask
import coloredlogs
from fastapi.middleware.cors import CORSMiddleware
from aiohttp import ClientSession , CookieJar


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
        "EH_USERNAME": "",
        "EH_PASSWORD": "",
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


def getConfig(key, default=None , require = True):  # 先检查环境变量 然后检查配置文件 如果default不空则返回default 否则报错
    if os.environ.get(key) != None:
        logger.info(f"config[{key}] from env", )
        return os.environ.get(key)
    if key in CONFIG and CONFIG[key] != "":
        logger.info(f"config[{key}] from config.json", )
        return CONFIG[key]
    if default != None:
        logger.info(f"config[{key}] using default : {default}")
        return default
    if require:
        logger.error(f"config [{key}] not found !")
        sys.exit(1)
    else:
        return None

EH_COOKIE = getConfig("EH_COOKIE", None , False)
if EH_COOKIE == None:
    if (EH_USERNAME := getConfig("EH_USERNAME", None , False)) and ( EH_PASSWORD := getConfig("EH_PASSWORD", None , False)):
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh',
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'dnt': '1',
            'origin': 'https://e-hentai.org',
            'priority': 'u=0, i',
            'referer': 'https://e-hentai.org/',
            'sec-ch-ua': '"Chromium";v="136", "Microsoft Edge";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0',
        }
        params = {
            'act': 'Login',
            'CODE': '01',
        }
        data = {
            'CookieDate': '1',
            'b': 'd',
            'bt': '1-1',
            'UserName': EH_USERNAME,
            'PassWord': EH_PASSWORD,
            'ipb_login_submit': 'Login!',
        }
        # response = requests.post('https://forums.e-hentai.org/index.php', params=params, headers=headers, data=data)
        async def getCookie(USERNAME, PASSWORD):
            async with ClientSession(cookie_jar=CookieJar()) as session:
                async with session.post('https://forums.e-hentai.org/index.php', params=params, headers=headers, data=data) as response:
                    if response.status == 200:
                        set_cookies = response.headers.getall('Set-Cookie', [])
                        logger.debug(str(set_cookies))
                        cookie_parts = [cookie.split(';', 1)[0] for cookie in set_cookies]
                        return '; '.join(cookie_parts)
                    else:
                        logger.error(f"获取cookie失败 {response.status}")
                        return None
        
        EH_COOKIE = serverLoop.run_until_complete(getCookie(EH_USERNAME, EH_PASSWORD))
        if EH_COOKIE  == None:
            logger.error("获取cookie失败")
            sys.exit(1)
        # logger.info(f"获取cookie成功 ")
        logger.info(f"获取cookie成功 {EH_COOKIE}",)
    else:
        logger.error("EH_COOKIE not found and EH_USERNAME , EH_PASSWORD not found !")
        sys.exit(1)


 
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

LINK_OR_MOVE = getConfig("LINK_OR_MOVE", 'move')
FAVORITE_DISABLED = getConfig("EH_FAVORITE_DISABLED", 'false')
DOWNLOAD_DISABLED = getConfig("EH_DOWNLOAD_DISABLED", 'false')
EH_COMMENT_DISABLED = getConfig("EH_COMMENT_DISABLED", 'false')
EH_RATE_DISABLED = getConfig("EH_RATE_DISABLED", 'false')
HISTORY_LIMIT = int(getConfig("EH_HISTORY_LIMIT", 200))
PORT = int(getConfig("PORT", 7964))
UTC_OFFSET = int(getConfig("UTC_OFFSET", getUTCOffset())) * 3600
setParserUtcOffset(UTC_OFFSET)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
    "Cookie": EH_COOKIE,
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
g_data_sseBinder = SSEDBMBinder(NOSQL_DB.table('g_data'), serverLoop, 'g_data')
download_sseBinder = SSEDBMBinder(NOSQL_DB.table('download'), serverLoop, 'download')
favorite_sseBinder = SSEDBMBinder(NOSQL_DB.table('favorite'), serverLoop, 'favorite')
card_info_sseBinder = SSEDBMBinder(NOSQL_DB.table('card_info'), serverLoop, 'card_info')
history_sseBinder = SSEDBMBinder(NOSQL_DB.table('history'), serverLoop, 'history')

SYNC_DICT_BINDERS = {
    'g_data': g_data_sseBinder,
    'download': download_sseBinder,
    'favorite': favorite_sseBinder,
    'card_info': card_info_sseBinder,
    'history': history_sseBinder,
}


async def subscribe_all_sync_dict(versions: dict):
    """合并所有syncDict频道的SSE订阅，单连接多路复用。"""
    q = asyncio.Queue()
    for binder in SYNC_DICT_BINDERS.values():
        binder.add_subscriber(q)
    try:
        for name, binder in SYNC_DICT_BINDERS.items():
            client_ver = versions.get(name, -1)
            if client_ver != binder.version:
                yield f"data: {json.dumps({'channel': name, 'action': LOAD, 'data': binder.getDict(), 'next': binder.version})}\n\n"
        while True:
            action = await q.get()
            yield f"data: {json.dumps(action)}\n\n"
    except (asyncio.CancelledError, GeneratorExit):
        pass
    finally:
        for binder in SYNC_DICT_BINDERS.values():
            binder.remove_subscriber(q)

aioPa = aoiAccessor(
    headers=headers,
    coverPath=COVER_PATH,
    cachePath=CACHE_PATH,
    galleryPath=GALLERY_PATH,
    link_or_move=LINK_OR_MOVE,
    db=NOSQL_DBS(
        g_data_sseBinder.getDBM(),
        download_sseBinder.getDBM(),
        favorite_sseBinder.getDBM(),
        card_info_sseBinder.getDBM(),
        EHDBM(NOSQL_DB.table('father_tree'), serverLoop, None),
        history_sseBinder.getDBM()
    ),
    loop=serverLoop,
    history_limit=HISTORY_LIMIT
)


app = FastAPI()


class SelectiveGZipMiddleware:
    """GZip中间件：普通请求用标准GZip，SSE流用Z_SYNC_FLUSH实时压缩"""
    def __init__(self, app, minimum_size=1000, compresslevel=6):
        self.app = app
        self.gzip_app = GZipMiddleware(app, minimum_size=minimum_size)
        self.compresslevel = compresslevel

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path", "").startswith("/api/sse/"):
            headers = Headers(scope=scope)
            if "gzip" in headers.get("Accept-Encoding", ""):
                responder = SSEGZipResponder(self.app, self.compresslevel)
                await responder(scope, receive, send)
                return
            await self.app(scope, receive, send)
        else:
            await self.gzip_app(scope, receive, send)


class SSEGZipResponder:
    """SSE专用GZip压缩：每个chunk用Z_SYNC_FLUSH刷新，浏览器可增量解压"""
    def __init__(self, app, compresslevel=6):
        self.app = app
        self.compresslevel = compresslevel
        self.send = None
        self.initial_message = None
        self.cobj = None
        self.started = False

    async def __call__(self, scope, receive, send):
        self.send = send
        await self.app(scope, receive, self.send_with_gzip)

    async def send_with_gzip(self, message):
        msg_type = message["type"]
        if msg_type == "http.response.start":
            self.initial_message = message
            return
        if msg_type != "http.response.body":
            await self.send(message)
            return

        body = message.get("body", b"")
        more_body = message.get("more_body", False)

        if not self.started:
            self.started = True
            self.cobj = zlib.compressobj(self.compresslevel, zlib.DEFLATED, 31)
            headers = MutableHeaders(raw=self.initial_message["headers"])
            headers["Content-Encoding"] = "gzip"
            headers.add_vary_header("Accept-Encoding")
            del headers["Content-Length"]
            await self.send(self.initial_message)

        if body:
            compressed = self.cobj.compress(body) + self.cobj.flush(zlib.Z_SYNC_FLUSH)
            message["body"] = compressed
        else:
            message["body"] = b""

        if not more_body:
            # 流结束，写出尾部
            trailer = self.cobj.flush(zlib.Z_FINISH)
            message["body"] += trailer
            message["more_body"] = False

        await self.send(message)


app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/sse/syncDict")
async def sse_sync_dict(request: Request,
                         g_data_version: int = -1,
                         download_version: int = -1,
                         favorite_version: int = -1,
                         card_info_version: int = -1,
                         history_version: int = -1):
    versions = {
        'g_data': g_data_version,
        'download': download_version,
        'favorite': favorite_version,
        'card_info': card_info_version,
        'history': history_version,
    }
    return StreamingResponse(
        subscribe_all_sync_dict(versions),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


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

@app.post("/api/fetch_g_data")
async def fetch_g_data(request: Request, gidList:gidTokenListBody):#批量获取g_data 使用官方接口
    if checkBlock(request):
        raise HTTPException(status_code=403, detail=str(
            makeTrackableException(None, "BLOCKED")))
    try:
        
        splittedList = [gidList.__root__[i:i+25] for i in range(0, len(gidList.__root__), 25)]
        g_data_list = []
        for gidListBlock in splittedList:
            for g_data in await aioPa.fetchG_dataOfficial(gidListBlock):
                g_data_list.append(g_data)
        return g_data_list
    except Exception as e:
        printTrackableException(e)
        raise HTTPException(status_code=500, detail=str(
            makeTrackableException(e, f"请求失败")))

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
                (await aioPa.makePDF(gid, token)).getvalue(),
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
        bytes = await aioPa.getGalleryPreviewBytes(gid, token, index)
        return Response(
            bytes,
            headers={"Content-Type": "image/jpeg",
                     "Cache-Control": "max-age=31536000"},
        )
    except Exception as e:
        printTrackableException(e)
        localBytes = aioPa.getGalleryPreviewFromLocal(gid, token, index)
        if localBytes:
            return Response(
                localBytes,
                headers={"Content-Type": "image/jpeg",
                         "Cache-Control": "max-age=31536000"},
            )
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
async def getDiskCacheSize():
    text = await aioPa.getDiskCacheSize()
    return {"msg": text}


@app.get("/api/clearDiskCache")
async def clearDiskCache():
    text = await aioPa.clearDiskCache()
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
    if HISTORY_LIMIT == 0:
        return {"msg": "history disabled"}
    await aioPa.addHistory(gid, token)
    return {"msg": "success"}


@app.get("/api/history/status")
async def historyStatus():
    return {"enabled": HISTORY_LIMIT != 0, "limit": HISTORY_LIMIT}


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


autoTaskInstance = autoTask(loop=serverLoop, aioPa=aioPa)

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
