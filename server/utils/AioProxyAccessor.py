import asyncio
from io import BytesIO
import json
import os
from os.path import join as path_join
import shutil
from typing import Coroutine, List, Union
from urllib.parse import parse_qs, urljoin
from zipfile import ZipFile
import time

from aiohttp import ClientSession, ClientTimeout, ClientResponse
from cacheout import LRUCache
from fastapi import HTTPException
from pydantic import BaseModel
from tinydb import Query
from utils.MakePDF import img2pdf
from utils.AsyncCacheWarper import AsyncCacheWarper
from utils.DBM import EHDBM, FAVORITE_STATE, DOWNLOAD_STATE
from utils.DownloadManager import downloadManager
from utils.HTMLParser import *
from utils.tools import checkImg, crop_image_with_offset, logger, makeTrackableException

# import heartrate
# heartrate.trace(browser=True)
from PIL import Image


class commentBody(BaseModel):
    gid: int
    token: str
    content: str
    edit: bool
    commentID: int


class downloadListBody(BaseModel):
    __root__: List[List[Union[int, str]]]


class gidTokenListBody(BaseModel):
    __root__: List[List[Union[int, str]]]


class NOSQL_DBS:
    def __init__(
        self,
        g_data_dbm: EHDBM,
        download_dbm: EHDBM,
        favorite_dbm: EHDBM,
        card_info_dbm: EHDBM,
        father_tree: EHDBM,
        history: EHDBM,
    ) -> None:
        self.g_data = g_data_dbm
        self.download = download_dbm
        self.favorite = favorite_dbm
        self.card_info = card_info_dbm
        self.father_tree = father_tree
        self.history = history


def getProxy():
    for name in ["HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"]:
        if os.environ.get(name, "") != "":
            return os.environ.get(name, "")
    return ""


timeOut = ClientTimeout(total=12)

styleMatch = re.compile(
    r"width:(\d+)px;height:(\d+)px;background:transparent url\(([^\)]+)\) -?(\d+)(?:px)? 0 (?:\/ )?(cover )?no-repeat"
)

# https://exhentai.org/g/3104752/bca9a0bf40
# width:198px;height:300px;background:transparent url(https://rainfxmohm.hath.network/gkgx8h786ctj5hwlq/209/186-dvvfn7bv.webp) 0 0 / cover no-repeat
# width:200px;height:299px;background:transparent url(https://s.exhentai.org/t/5d/6e/5d6e2352ae5418d69b64bf9037f117e379cd51ec-4415280-2444-3648-jpg_l.jpg) 0 0 no-repeat

# https://exhentai.org/g/3129446/7d326c857c
# width:83px;height:300px;background:transparent url(https://puzaqhxrbn.hath.network/c2/ir9aqalccb6cj2wlp/3129446-0.webp) -200px 0 no-repeat

# https://exhentai.org/g/3129502/5136351a0e
# width:200px;height:113px;background:transparent url(https://praogxqcch.hath.network/c2/kv6n4fe5x709e0wlr/3129502-0.webp) -400px 0 no-repeat

# https://exhentai.org/g/3129575/3623a505de
# width:200px;height:282px;background:transparent url(https://sunvxqrqcj.hath.network/c2/k05elwigp69gzmwlr/3129575-0.webp) -400px 0 no-repeat


# https://exhentai.org/g/3129446/7d326c857c
# width:83px;height:300px;background:transparent url(https://puzaqhxrbn.hath.network/c2/diau8fyfbshmjnwlr/3129446-0.webp) -200px 0 no-repeat

# https://exhentai.org/g/3128567/2710e63716
# width:200px;height:284px;background:transparent url(https://sunvxqrqcj.hath.network/c2/v36bbpbaoob822wlq/3128567-0.webp) -0px 0 no-repeat


class aoiAccessor:
    def __init__(
        self,
        headers: dict,
        coverPath: str,
        cachePath: str,
        galleryPath: str,
        db: NOSQL_DBS,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.headers = headers
        self.coverPath = coverPath
        self.cachePath = cachePath
        self.galleryPath = galleryPath
        self.cache_html = LRUCache(maxsize=512, default=None)
        self.cache_cardInfo = LRUCache(maxsize=512, default=None)
        # 下载时可以用， 获取g_data 然后更新数据库和此cache
        # 注意这个与数据库的cardInfo格式不同的 是他的超集
        self.cache_g_data = LRUCache(maxsize=512, default=None)
        self.proxy = getProxy()
        if self.proxy != "":
            logger.info(f"使用代理 {self.proxy}")
        self.db = db
        self.loop = loop
        self.downloadManagerInstance = downloadManager(self)
        self.session = ClientSession()  # loop=loop
        self.loop.create_task(self.inlineSetOnInit())

        for gid in self.db.download:  # 初始化时 清除下载状态
            if self.db.download[gid]["state"] != DOWNLOAD_STATE.FINISHED:
                logger.warning(f"{gid} 下载状态已重置")
                self.db.download[gid]["state"] = DOWNLOAD_STATE.FINISHED
        # [
        #     self.loop.create_task(self.updateCardInfo(res["gid"],res["token"]))
        #     for res in self.db.download.getDict().values()
        # ]

    async def inlineSetOnInit(self):
        # try:
        #     await self.getHtml("https://exhentai.org/?inline_set=ts_l", cached=False)
        # except Exception as e:
        #     logger.error(f"set / to Thumbnail failed: {e}")
        # 现在已经可以处理所有主页的情况了
        try:
            await self.getHtml("https://exhentai.org/?inline_set=dm_t", cache=False)
        except Exception as e:
            logger.error(f"set /g/ to large failed: {e}")

    def __del__(self):
        self.loop.run_until_complete(self.session.close())

    def getUrlTTL(self, url):
        if ".org/g/" in url:
            return None
        elif ".org/s/" in url:
            return 60
        else:
            return None

    @AsyncCacheWarper(
        cacheContainer=LRUCache(maxsize=512, ttl=3, default=None),
    )
    async def getHtmlAlwaysCache(self, url: str):
        # cache 但是ttl极短
        # 仅用于短时间内大量请求
        # 需要外部函数调用 并单独缓存
        try:
            resp = await self.session.get(
                url, headers=self.headers, proxy=self.proxy, timeout=timeOut
            )
            html = await resp.text()
            removeIndex = html.find("<html")
            if removeIndex != -1:
                html = html[removeIndex:]
            return html
        except Exception as e:
            raise e

    async def getHtml(self, url: str, cache=True):
        """
        默认使用缓存
        """
        if cache and self.cache_html.has(url):
            return self.cache_html.get(url)
        try:
            result = await self.getHtmlAlwaysCache(url)
            self.cache_html.set(key=url, value=result, ttl=self.getUrlTTL(url))
            return result
        except Exception as e:
            raise makeTrackableException(e, f"getHtml({url})")

    async def httpGet(self, url) -> ClientResponse:
        return await self.session.get(
            url, headers=self.headers, proxy=self.proxy, timeout=timeOut
        )

    @AsyncCacheWarper(
        cacheContainer=LRUCache(maxsize=512, ttl=3 , default=None),
    )
    async def downloadImgBytes(self, url: str):
        """
        下载url 返回bytes
        """
        try:
            resp = await self.httpGet(url)
            bytes = await resp.read()
            if checkImg(bytes):
                return bytes
            else:
                raise Exception(f"checkImg({url}) failed")
        except Exception as e:
            traceback.print_exc()
            raise makeTrackableException(e, f"download({url}) -> bytes failed")

    async def downloadImg(self, url, filePath):
        try:
            bytes = await self.downloadImgBytes(url)
            with open(filePath, "wb") as f:
                f.write(bytes)
        except Exception as e:
            raise makeTrackableException(e, f"downloadImgBytes({url}, {filePath})")

    # @printPerformance
    def updateLocalFavorite(self, gid: int, index: int):  # -1 未收藏 0-9 对应收藏夹
        # logger.info(f"self.db.favorite[{gid}]({type(gid)}) = {self.db.favorite[gid]}")
        if index == -1:
            if self.db.favorite[gid] != None:
                logger.info(f"{gid} 删除本地收藏")
                del self.db.favorite[gid]
                return
        else:
            if self.db.favorite[gid] == None:
                logger.info(f"{gid} 添加本地收藏记录 index={index}")
                self.db.favorite[gid] = {
                    "gid": gid,
                    "state": FAVORITE_STATE.FAVORITED,
                    "index": index,
                }
            elif self.db.favorite[gid]["index"] != index:
                logger.info(f"{gid} 更新本地收藏记录 index={index}")
                self.db.favorite[gid]["index"] = index

    async def addFavorite(self, gid, token, index) -> None:
        if (
            gid in self.db.favorite
            and self.db.favorite[gid]["state"] == FAVORITE_STATE.FAVORITED
        ):
            return
        url = f"https://exhentai.org/gallerypopups.php?gid={gid}&t={token}&act=addfav"
        data = {"favcat": str(index), "favnote": "", "update": "1"}
        try:
            prev = self.db.favorite[gid]
            self.db.favorite[gid] = {
                "gid": gid,
                "state": FAVORITE_STATE.FETCHING,
                "index": index,
            }
            response = await self.session.post(
                url=url,
                headers=self.headers,
                data=data,
                proxy=self.proxy,
                timeout=timeOut,
            )
            await response.text()
            if response.ok:
                self.db.favorite[gid] = {
                    "gid": gid,
                    "state": FAVORITE_STATE.FAVORITED,
                    "index": index,
                }
            else:
                self.db.favorite[gid] = prev
                raise Exception(
                    f"addFavorite({gid}, {index}) response.code={response.status_code}"
                )
        except Exception as e:
            if prev == None:
                del self.db.favorite[gid]
            else:
                self.db.favorite[gid] = prev
            raise Exception(makeTrackableException(e, f"addFavorite({gid}, {index})"))

    async def rmFavorite(self, gid, token) -> None:
        url = f"https://exhentai.org/gallerypopups.php?gid={gid}&t={token}&act=addfav"
        data = {
            "favcat": "favdel",
            "favnote": "",
            "apply": "Apply Changes",
            "update": "1",
        }
        try:
            prev = self.db.favorite[gid]
            self.db.favorite[gid] = {
                "gid": gid,
                "state": FAVORITE_STATE.FETCHING,
                "index": 999,
            }
            response = await self.session.post(
                url=url,
                headers=self.headers,
                data=data,
                proxy=self.proxy,
                timeout=timeOut,
            )
            await response.text()
            if response.ok and self.db.favorite[gid] != None:
                del self.db.favorite[gid]
            else:
                if prev != None:
                    self.db.favorite[gid] = prev
                raise Exception(
                    f"rmFavorite({gid},{token}) response.code={response.status_code}"
                )
        except Exception as e:
            if prev != None:
                self.db.favorite[gid] = prev
            raise Exception(makeTrackableException(e, f"rmFavorite({gid},{token})"))

    async def fetchG_dataOfficial(self, gidList) -> List[object]:  # 只有下载才用得到
        try:
            resp = await self.session.post(
                url="https://exhentai.org/api.php",
                json={
                    "method": "gdata",
                    "gidlist": gidList,
                    "namespace": 1,
                },
                headers=self.headers,
                proxy=self.proxy,
                timeout=timeOut,
            )
            text = await resp.text()
            g_data_list = json.loads(text)["gmetadata"]
            for item in g_data_list:
                self.cache_g_data.set(int(item["gid"]), item)  # 仍然更新cache
            return g_data_list
        except Exception as e:
            raise e

    async def get_G_data(self, gid, token, cache, countOnly):
        # 虽然说是G_DATA 实际上并不是官方的接口
        # 普通请求直接用
        # 画廊请求带nocache的时候 记得cache=False
        if countOnly and self.cache_cardInfo.has(gid):
            return {
                "filecount": str(self.cache_cardInfo.get(gid)["pages"]),
                "title": self.cache_cardInfo.get(gid)["name"],
            }
        if cache and self.cache_g_data.has(gid):
            # logger.info(f"cache hit {gid}")
            return self.cache_g_data.get(gid)
        dbSearch = self.db.g_data[gid]
        if cache and dbSearch != None:
            self.cache_g_data.set(gid, dbSearch)
            logger.info(f"query success {gid}")
            return dbSearch
        logger.info(f"get_G_data({gid}) from html")
        try:
            html = await self.getHtml(
                f"https://exhentai.org/g/{gid}/{token}/?p=0", cache=cache
            )
            g_data = getG_dataFromGalleryPage(html)
            self.updateLocalFavorite(gid, g_data["extended"]["favoriteIndex"])
            self.cache_g_data.set(gid, g_data)
            return g_data
        except Exception as e:
            if self.cache_g_data.has(gid):
                return self.cache_g_data.get(gid)
            if self.db.g_data[gid]:
                return self.db.g_data[gid]
            raise makeTrackableException(e, f"get_G_data({gid}, {token}, {cache})")

    async def getGalleryCoverIgnoreError(self, gid, token, delay=0):
        try:
            await asyncio.sleep(delay / 1000)
            return await self.getGalleryCover(gid, token)
        except Exception as e:
            logger.warning(f"getGalleryCoverIgnoreError({gid}, {token}) {e}")
            return None

    def updateCardCacheAndFavorite(self, cardInfos):
        for index, cardInfo in enumerate(cardInfos):
            self.cache_cardInfo.set(cardInfo["gid"], cardInfo)
            self.updateLocalFavorite(cardInfo["gid"], cardInfo["favoriteIndex"])
            # self.loop.create_task(self.getGalleryCoverIgnoreError(cardInfo['gid'], cardInfo['token'], index * 20))
            # 预加载封面

    # @printPerformance

    async def getMainPageGalleryCardInfo(self, url: str):
        """
        获取主页面的卡片信息
        """
        try:
            html = await self.getHtml(url, cache=False)
            cardInfos = parseMainPage(html)
            self.updateCardCacheAndFavorite(cardInfos)
            return cardInfos
        except Exception as e:
            raise makeTrackableException(e, f"getMainPageGalleryCardInfo({url})")

    async def getComments(self, gid, token, fetchAll=False):
        try:
            if fetchAll:
                html = await self.getHtml(
                    f"https://exhentai.org/g/{gid}/{token}/?hc=1#comments", cache=False
                )
            else:
                html = await self.getHtml(
                    f"https://exhentai.org/g/{gid}/{token}/?p=0", cache=True
                )
            return getCommentsFromGalleryPage(html)
        except Exception as e:
            raise makeTrackableException(e, f"getComments({gid}, {token}, {fetchAll})")

    def parseG_dataToCardInfo(self, g_data):
        return {
            "type": CardInfoType.FROM_G_DATA,
            "gid": g_data["gid"],
            "token": g_data["token"],
            "imgSrc": "/cover/{}_{}.jpg".format(g_data["gid"], g_data["token"]),
            "rawSrc": g_data["thumb"],
            "name": g_data["title_jpn"] or g_data["title"],
            "rank": g_data["rating"],
            "category": g_data["category"],
            "uploadTime": timestamp_to_str("%Y-%m-%d %H:%M", int(g_data["posted"])),
            "lang": "chinese" if "language:chinese" in g_data["tags"] else "",
            "pages": g_data["filecount"],
            # 用于刷新本地状态 前端用不到 因为前端靠全局状态判断favorite和download
            "favoriteIndex": (
                self.db.favorite[g_data["gid"]]["index"]
                if self.db.favorite[g_data["gid"]]
                else -1
            ),
            "tags": g_data["tags"],
        }

    @printPerformance
    def localSearch(self, query):
        str = parse_qs(query)["f_search"][0]
        tagRe = '[A-Za-z0-9]+:"[^\$]+\$"'
        wordRe = "[\u0800-\u4e00\u4E00-\u9FA5A-Za-z0-9_]+"
        tags = []
        for tagRes in re.findall(tagRe, str):
            str = str.replace(tagRes, "")
            tags.append(re.sub('\$|"', "", tagRes))
        words = re.findall(wordRe, str)

        logger.info(f"localSearch words: {json.dumps(words, ensure_ascii=False)}")
        logger.info(f"localSearch tags: {json.dumps(tags)}")

        def checkTitle(title):
            for word in words:
                if word not in title:
                    return False
            return True

        downloadedGid = tuple(self.db.download.keys())
        return sorted(
            [
                self.parseG_dataToCardInfo(g_data)
                for g_data in self.db.g_data.search(
                    (Query().tags.all(tags))
                    & (
                        (Query().title.test(checkTitle))
                        | Query().title_jpn.test(checkTitle)
                    )
                    & (Query().gid.one_of(downloadedGid))
                )
            ],
            key=lambda x: self.db.download[x["gid"]]["index"],
            reverse=True,
        )

    def checkGalleryImageLocal(
        self, gid, token, index
    ) -> str:  # index从一开始 仅检测本地是否存在
        cachePath = path_join(self.cachePath, f"{gid}_{token}_{index:08d}.jpg")
        if os.path.exists(cachePath):
            return cachePath
        localPath = path_join(
            self.galleryPath,
            path_join("{}_{}".format(gid, token), f"{index:08d}.jpg"),
        )
        if os.path.exists(localPath):
            return localPath
        return None

    async def getGalleryImage(self, gid, token, index) -> str:  # index 从一开始
        localImg = self.checkGalleryImageLocal(gid, token, index)
        cachePath = path_join(self.cachePath, f"{gid}_{token}_{index:08d}.jpg")
        if localImg:
            return localImg
        try:
            galleryPageUrl = (
                f"https://exhentai.org/g/{gid}/{token}/?p={(index - 1) // 20}"
            )
            galleryPageHtml = await self.getHtml(galleryPageUrl, cache=True)
            viewInfo = getViewInfoFromPage(galleryPageHtml)
            viewPageUrl, _ = viewInfo[(index - 1) % 20]
            viewPageHtml = await self.getHtml(viewPageUrl, cache=True)
            skipHathKey, imgSrc = getInfoFromViewingPage(viewPageHtml)
            # 获取galleryPage并获取viewPage
            # 两个有一个出错都直接raise

        except Exception as e:
            raise makeTrackableException(e, f"getGalleryImage({gid}, {token}, {index})")
        if imgSrc.endswith("/509.gif"):
            raise HTTPException(
                status_code=509,
                detail=str(
                    makeTrackableException(
                        f"getGalleryImage({gid}, {token}, {index})", f"已到达限额"
                    )
                ),
            )
        try:
            await self.downloadImg(imgSrc, cachePath)
            # 下载成功则直接返回
            return cachePath
        except Exception as e:
            # 失败 则报错 然后尝试skipHathKey
            logger.warning(
                f"downloadImg $CACHE/{gid}_{token}_{index:08d}.jpg failed, try to download using skipHathKey"
            )
        try:
            skipHathKeyViewPageUrl = viewPageUrl + "?nl=" + skipHathKey
            skipHathKeyViewPageHtml = await self.getHtml(
                skipHathKeyViewPageUrl, cache=True
            )
            _, skipHathKeyImgSrc = getInfoFromViewingPage(skipHathKeyViewPageHtml)
            await self.downloadImg(skipHathKeyImgSrc, cachePath)
            logger.info(
                f"downloadImg $CACHE/{gid}_{token}_{index:08d}.jpg using skipHathKey success"
            )
            return cachePath
        except Exception as e:
            logger.error(
                f"downloadImg $CACHE/{gid}_{token}_{index:08d}.jpg using skipHathKey failed"
            )
            raise makeTrackableException(e, f"getGalleryImage({gid}, {token}, {index})")

    def getGalleryPreviewFromLocal(self, gid, token, index) -> bytes:
        localPath = self.checkGalleryImageLocal(gid, token, index)  # width = 200
        if localPath:
            image = Image.open(localPath)
            height = int((float(image.size[1]) / image.size[0]) * 200)
            resized_image = image.resize((200, height))
            byte_stream = BytesIO()
            resized_image.save(byte_stream, format="JPEG")
            return byte_stream.getvalue()
        return None

    async def getGalleryPreviewBytes(self, gid, token, index) -> bytes:
        """
        E站改版，预览图片有两种：
        一是和之前一样，单张图片
        二是将所有封面存在一张图片，使用DIV裁切与偏移实现预览图片的显示
        """
        try:
            galleryPageUrl = (
                f"https://exhentai.org/g/{gid}/{token}/?p={(index - 1) // 20}"
            )
            galleryPageHtml = await self.getHtml(galleryPageUrl, cache=True)
            _, styleText = getViewInfoFromPage(galleryPageHtml)[(index - 1) % 20]
            matched = styleMatch.findall(styleText)
            # print(matched)
            if len(matched) == 0:
                raise Exception("Preview match error style : " + styleText)

            width = int(matched[0][0])  # div尺寸
            height = int(matched[0][1])
            url = matched[0][2]  # 图片链接
            offset_x = int(matched[0][3])  # 偏移量
            cover = matched[0][4] == "cover"  # cover模式
            imgBytes = await self.downloadImgBytes(url)
            if cover:
                # 单图
                assert offset_x == 0, "不能又是cover模式，又是一堆图打包的"
                return imgBytes
            else:
                # 多图裁切
                rawImg = Image.open(BytesIO(imgBytes))
                resultBytes = BytesIO()
                offsetImg = rawImg.crop((offset_x, 0, offset_x + width, height))
                offsetImg.save(resultBytes, format="PNG")
            return resultBytes.getvalue()
        except Exception as e:
            raise makeTrackableException(
                e, f"getGalleryPreviewBytes({gid}, {token}, {index})"
            )

    # @printPerformance
    @AsyncCacheWarper(
        cacheContainer=LRUCache(maxsize=512, ttl=1, default=None),
    )
    async def getGalleryCover(self, gid, token) -> str:
        cachePath = path_join(self.cachePath, f"{gid}_{token}.jpg")
        if os.path.exists(cachePath):
            return cachePath
        downloadPath = path_join(self.coverPath, f"{gid}_{token}.jpg")
        if os.path.exists(downloadPath):
            return downloadPath
        try:
            if self.cache_cardInfo.has(gid) and self.cache_cardInfo.get(gid) != None:
                # src = self.cache_cardInfo.get(gid)['rawSrc'].replace(
                #     "exhentai.org", "ehgt.org")
                src = self.cache_cardInfo.get(gid)["rawSrc"]
                await self.downloadImg(src, cachePath)
                return cachePath
            if self.cache_g_data.has(gid) and self.cache_cardInfo.get(gid) != None:
                # src = self.cache_cardInfo.get(gid)['rawSrc'].replace(
                #     "exhentai.org", "ehgt.org")
                src = self.cache_cardInfo.get(gid)["rawSrc"]
                await self.downloadImg(src, cachePath)
                return cachePath
            g_data = await self.get_G_data(gid, token, cache=True, countOnly=False)
            # src = g_data['thumb'].replace("exhentai.org", "ehgt.org")
            src = g_data["thumb"]
            await self.downloadImg(src, cachePath)
            return cachePath
        except Exception as e:
            # traceback.print_exc()
            raise makeTrackableException(e, f"getGalleryCover({gid}, {token})")

    async def addDownload(self, gidList) -> None:  # 以后改成单个的
        for gid, token in gidList:
            await self.downloadManagerInstance.addDownload(int(gid), token, None)

    async def addListDownload(self, gidList: list) -> None:  # 有error 直接throw
        splittedList = [gidList[i : i + 25] for i in range(0, len(gidList), 25)]
        g_data_map = {}
        count = 0
        for gidListBlock in splittedList:
            count += 1
            for g_data in await self.fetchG_dataOfficial(gidListBlock):
                g_data_map[int(g_data["gid"])] = g_data
            logger.info(f"add list download G_DATA fetch {count}/{len(splittedList)}")
        for gid, token in gidList:
            assert int(gid) in g_data_map
        [
            self.loop.create_task(
                self.downloadManagerInstance.addDownload(
                    int(gid), token, g_data_map[int(gid)]
                )
            )
            for (gid, token) in gidList
        ]

    async def deleteDownload(self, gidList) -> None:
        for gid, token in gidList:
            await self.downloadManagerInstance.deleteDownload(int(gid), token)

    async def continueDownload(self) -> int:
        g_data_table = self.db.g_data.getDict()
        downloadTable = self.db.download.getDict()
        unFinishList = []
        for gid in downloadTable:  # 队列中 下载中 跳过
            if downloadTable[gid]["state"] == DOWNLOAD_STATE.NOW_DOWNLOADING:
                continue
            if downloadTable[gid]["state"] == DOWNLOAD_STATE.IN_QUEUE:
                continue
            if gid in g_data_table and downloadTable[gid]["success"] == int(
                g_data_table[gid]["filecount"]
            ):
                continue
            else:
                unFinishList.append(
                    (downloadTable[gid]["gid"], downloadTable[gid]["token"])
                )
        g_data_map = {(gid, token): None for (gid, token) in unFinishList}
        # 数组分割成25个一组
        splittedUnFinishList = [
            unFinishList[i : i + 25] for i in range(0, len(unFinishList), 25)
        ]
        for gidList in splittedUnFinishList:
            for g_data in await self.fetchG_dataOfficial(gidList):
                g_data_map[int(g_data["gid"])] = g_data

        [
            self.loop.create_task(
                self.downloadManagerInstance.addDownload(
                    int(gid), token, g_data_map[int(gid)]
                )
            )
            for (gid, token) in unFinishList
        ]
        return len(unFinishList)

    async def updateCardInfo(self, gid: int, token: str):
        logger.debug(f"updateCardInfo({gid}, {token})")
        if self.cache_cardInfo.has(gid):
            cachedCard = self.cache_cardInfo.get(gid)
            self.db.card_info[gid] = {
                "gid": gid,
                "token": token,
                "name": cachedCard["name"],
                "rank": cachedCard["rank"],
                "category": cachedCard["category"],
                "uploadTime": cachedCard["uploadTime"],
                "lang": cachedCard["lang"],
                "pages": cachedCard["pages"],
            }
            logger.debug(f"updateCardInfo({gid}, {token}) from cached card")
        else:
            try:
                g_data = await self.get_G_data(gid, token, cache=True, countOnly=False)
                self.db.card_info[gid] = {
                    "gid": g_data["gid"],
                    "token": g_data["token"],
                    "name": g_data["title_jpn"] or g_data["title"],
                    "category": g_data["category"],
                    "uploadTime": time.strftime(
                        "%Y-%m-%d %H:%M", time.localtime(int(g_data["posted"]))
                    ),
                    "lang": "chinese" if "language:chinese" in g_data["tags"] else "",
                    "rank": g_data["rating"],
                    "pages": int(g_data["filecount"]),
                }
                logger.debug(f"updateCardInfo({gid}, {token}) from get_G_data")
            except Exception as e:
                logger.error(f"updateCardInfo({gid}, {token}) failed")
                pass

    # @printPerformance
    def getNowDownloadIndex(self) -> int:
        indexList = [item["index"] for item in self.db.download.getDict().values()]
        if len(indexList) == 0:
            return 0
        return max(indexList) + 1

    def getDiskCacheSize(self) -> str:
        size = sum(
            os.path.getsize(path_join(self.cachePath, file))
            for file in os.listdir(self.cachePath)
        )
        return f"{size / 1024 / 1024:.2f}MB"

    def clearDiskCache(self) -> str:
        size = self.getDiskCacheSize()
        # shutil.rmtree(self.cachePath, ignore_errors=True)
        # os.makedirs(self.cachePath , exist_ok=True)
        for file in os.listdir(self.cachePath):
            os.remove(path_join(self.cachePath, file))
        return size

    async def addDownloadRecordFromZip(self, gid, token, zipBytes):
        extNames = ["jpg", "JPG", "png", "PNG", "gif", "GIF"]
        z = ZipFile(BytesIO(zipBytes))
        files = [
            file for file in z.filelist if file.filename.split(".")[-1] in extNames
        ]
        files.sort(key=lambda x: x.filename)
        extractDir = path_join(self.cachePath, f"{gid}_{token}_extract")
        z.extractall(extractDir)
        for index, file in enumerate(files):
            cachePath = path_join(self.cachePath, f"{gid}_{token}_{(index+1):08d}.jpg")
            extractedPath = path_join(extractDir, file.filename)
            (
                shutil.move(extractedPath, cachePath)
                if not os.path.exists(cachePath)
                else None
            )
            logger.debug(f"mv {extractedPath} -> {cachePath}")
        await self.addDownload([[gid, token]])

    async def reUpdateLocalG_data(self, count=0):
        """
        更新本地g_data表与文件夹内的g_data.json
        count: 更新的数量 从最新的开始向后检查
        count为0时 更新所有
        """
        download_rec = self.db.download.getDict().values()
        if count == 0:
            gidList = sorted(download_rec, key=lambda x: x["index"], reverse=True)
        else:
            gidList = sorted(download_rec, key=lambda x: x["index"], reverse=True)[
                :count
            ]
        splittedList = [gidList[i : i + 25] for i in range(0, len(gidList), 25)]
        successCount = 0
        for recList in splittedList:
            try:
                res = await self.fetchG_dataOfficial(
                    [[rec["gid"], rec["token"]] for rec in recList]
                )
                successCount += len(res)
                for g_data in res:
                    if json.dumps(self.db.g_data[g_data["gid"]]) == json.dumps(g_data):
                        logger.debug(f"g_data of {g_data['gid']} is up to date")
                    else:
                        logger.debug(f"g_data of {g_data['gid']} updated")
                        self.db.g_data[g_data["gid"]] = g_data
                        saveDir = path_join(
                            self.galleryPath, f"{g_data['gid']}_{g_data['token']}"
                        )
                        g_data_json_save_path = path_join(saveDir, "g_data.json")
                        with open(g_data_json_save_path, "w", encoding="utf-8") as f:
                            json.dump(g_data, f, ensure_ascii=True, indent=4)
                    await self.updateCardInfo(g_data["gid"], g_data["token"])
                logger.info(f"reUpdateLocalG_data {successCount}/{count}")
                await asyncio.sleep(5)  # 减少服务器压力
            except Exception as e:
                logger.error(f"reUpdateLocalG_data error {str(e)}")
                pass
        logger.info(f"reUpdateLocalG_data finished")

    async def rateGallery(self, gid: int, token: str, score: float):
        if score < 0 or score > 5:
            raise Exception(f"illegal score {score} , should be between 0 and 5")
        html = await self.getHtml(
            f"https://exhentai.org/g/{gid}/{token}/?p=0", cache=True
        )
        apiUid = int(re.findall(r"var apiuid = ([^;]+);", html)[0])
        apiKey = re.findall(r"var apikey = \"([^;]+)\";", html)[0]
        json_data = {
            "method": "rategallery",
            "apiuid": apiUid,
            "apikey": apiKey,
            "gid": gid,
            "token": token,
            "rating": int(score * 2),
        }
        try:
            response = await self.session.post(
                url="https://exhentai.org/api.php",
                headers=self.headers,
                json=json_data,
                proxy=self.proxy,
                timeout=timeOut,
            )
            if response.ok:
                result = json.loads(await response.text())
                return {
                    "averageRating": result["rating_avg"],
                    "ratingCount": result["rating_cnt"],
                    "userRankColor": CLASS_RATING_COLOR_MAP[result["rating_cls"]],
                    "userRankValue": result["rating_usr"],
                }
            else:
                raise Exception(
                    f"rateGallery({gid},{token}) response.code={response.status_code}"
                )
        except Exception as e:
            raise makeTrackableException(e, f"rateGallery({gid},{token})")

    async def voteComment(self, gid: int, token: str, commentID: int, vote: int):
        if vote != 1 and vote != -1:
            raise Exception(f"illegal vote {vote} , should be 1 or -1")
        html = await self.getHtml(
            f"https://exhentai.org/g/{gid}/{token}/?p=0", cache=True
        )
        apiUid = int(re.findall(r"var apiuid = ([^;]+);", html)[0])
        apiKey = re.findall(r"var apikey = \"([^;]+)\";", html)[0]
        json_data = {
            "method": "votecomment",
            "apiuid": apiUid,
            "apikey": apiKey,
            "gid": gid,
            "token": token,
            "comment_id": commentID,
            "comment_vote": vote,
        }
        try:
            response = await self.session.post(
                url="https://exhentai.org/api.php",
                headers=self.headers,
                json=json_data,
                proxy=self.proxy,
                timeout=timeOut,
            )
            if response.ok:
                result = json.loads(await response.text())
                return {
                    "commentID": result["comment_id"],
                    "score": (
                        str(result["comment_score"])
                        if result["comment_score"] <= 0
                        else f'+{result["comment_score"]}'
                    ),
                    "vote": result["comment_vote"],
                }
            else:
                raise Exception(
                    f"voteComment({gid},{token},{commentID},{vote}) response.code={response.status_code}"
                )
        except Exception as e:
            raise makeTrackableException(
                e, f"voteComment({gid},{token},{commentID},{vote})"
            )

    async def postComment(self, comment: commentBody):
        if comment.edit:
            data = {
                "edit_comment": str(comment.commentID),
                "commenttext_edit": comment.content,
            }
        else:
            data = {
                "commenttext_new": comment.content,
            }

        response = await self.session.post(
            url=f"https://exhentai.org/g/{comment.gid}/{comment.token}/",
            headers=self.headers,
            data=data,
            proxy=self.proxy,
            timeout=timeOut,
        )
        if response.ok:
            html = await response.text()
            return getCommentsFromGalleryPage(html)
        else:
            raise Exception(
                f"postComment({comment.gid},{comment.token},{comment.content}) response.code={response.status_code}"
            )

    async def getGalleryPreviewIgnoreError(self, gid, token, index):
        try:
            return await self.getGalleryPreviewBytes(gid, token, index)
        except Exception as e:
            logger.warning(f"getGalleryPreviewIgnoreError({gid}, {token}) {e}")
            return None

    async def getPreviewSrcIndexMap(self, gid, token):  # 获取src对应index的映射

        g_data = await self.get_G_data(gid, token, cache=True, countOnly=False)
        filecount = int(g_data["filecount"])

        tasks = [
            asyncio.create_task(self.getGalleryPreviewIgnoreError(gid, token, i + 1))
            for i in range(filecount)
        ]

        previewBytesList = await asyncio.gather(*tasks)
        return {
            src: {
                "index": i + 1,
                "gid": gid,
                "token": token,
            }
            for i, src in enumerate(previewBytesList)
            if src != None
        }

    async def checkParents(
        self, gid, token
    ):  # 检查是否有已下载的父画廊 返回最近的 无则空
        if self.db.g_data[gid]:
            g_data = self.db.g_data[gid]
        else:
            g_data = (await self.fetchG_dataOfficial([[gid, token]]))[0]
        if "parent_gid" not in g_data:
            return None
        searchRes = self.db.g_data.search(
            (
                (Query().parent_gid == int(g_data["parent_gid"]))
                | (Query().gid == int(int(g_data["parent_gid"])))
            )
            & (Query().gid != gid)
        )
        return sorted(searchRes, key=lambda x: x["gid"])

    async def parentImgMultiplex(self, gid, token):  # 父画廊文件复用
        try:
            parents = await self.checkParents(gid, token)
            if parents:
                logger.info("存在父画廊,准备复用本地文件")
                new = await self.getPreviewSrcIndexMap(gid, token)
                old = await self.getPreviewSrcIndexMap(
                    parents[0]["gid"], parents[0]["token"]
                )
                needDownload = []
                for bytes in new:
                    if bytes in old:
                        src = await self.getGalleryImage(
                            old[bytes]["gid"], old[bytes]["token"], old[bytes]["index"]
                        )
                        dst = path_join(
                            self.cachePath,
                            f"{gid}_{token}_{new[bytes]['index']:08d}.jpg",
                        )
                        if not os.path.exists(dst):
                            shutil.copy(src, dst)
                    else:
                        needDownload.append(new[bytes]["index"])
                logger.info(f"复用父画廊文件 {len(new) - len(needDownload)}/{len(new)}")
                logger.info("复用后需要下载" + str(needDownload))
        except Exception as e:
            logger.error("复用文件出错 : " + str(e))

    async def deleteOldGallery(self):
        res = await self.updateFatherTree()
        logger.info(f"total update {res} galleries in father_tree")
        as_father = set()
        for gid in self.db.father_tree:
            as_father.add(self.db.father_tree[gid]["f_gid"])
        old_gallery = as_father & set(self.db.download.keys())
        for gid in old_gallery:
            token = self.db.download[gid]["token"]
            await self.deleteDownload([[gid, token]])
        return len(old_gallery)

    async def updateFatherTree(self):  # 更新father_tree表 删除旧版本画廊
        for gid in self.db.download:
            if gid not in self.db.father_tree:
                self.db.father_tree[gid] = {
                    "gid": gid,
                    "token": self.db.download[gid]["token"],
                    "f_gid": "",
                    "f_token": "",
                }
        need_update_gid_list = [
            gid
            for gid in self.db.father_tree.keys()
            if self.db.father_tree[gid]["f_gid"] == ""
        ]
        if len(need_update_gid_list) == 0:
            return 0
        logger.info(
            f"{len(need_update_gid_list)} galleries need to update in father_tree"
        )
        splitted = [
            need_update_gid_list[i : i + 25]
            for i in range(0, len(need_update_gid_list), 25)
        ]
        for gid_list_x25 in splitted:
            try:
                gid_token_list = [
                    [gid, self.db.father_tree[gid]["token"]] for gid in gid_list_x25
                ]
                for g_data in await self.fetchG_dataOfficial(gid_token_list):
                    assert "title" in g_data, "g_data error"
                    if "parent_gid" in g_data:
                        self.db.father_tree[g_data["gid"]] = (
                            {  # 这里注意  虽然画廊gid是int 但是father_tree的gid是str
                                "gid": g_data["gid"],
                                "token": g_data["token"],
                                "f_gid": int(g_data["parent_gid"]),
                                "f_token": g_data["parent_key"],
                            }
                        )
                        if int(g_data["parent_gid"]) not in self.db.father_tree:
                            self.db.father_tree[int(g_data["parent_gid"])] = {
                                "gid": int(g_data["parent_gid"]),
                                "token": g_data["parent_key"],
                                "f_gid": "",
                                "f_token": "",
                            }
                    else:
                        self.db.father_tree[g_data["gid"]] = {
                            "gid": g_data["gid"],
                            "token": g_data["token"],
                            "f_gid": "_",
                            "f_token": "_",
                        }
            except Exception as e:
                logger.error(
                    f"updateFatherTree error : {e} , ignored and retry in next loop"
                )
        return len(need_update_gid_list) + await self.updateFatherTree()

    def listAllDownload(
        self,
    ):
        return self.db.download.getDict()

    async def syncFromOtherServer(self, notify: Coroutine, recv: Coroutine):
        # 从其他服务器同步画廊
        # notify: 通知前端当前进度
        # recv: 接收前端传来的参数
        # 前端连接，传递目标url
        # 这里尝试连接，失败则通知error
        targetServerUrl = json.loads((await recv()))["url"]
        try:
            remoteDownloadData = await (
                await self.httpGet(targetServerUrl + "/api/listAllDownload")
            ).json()
        except Exception as e:
            await notify(json.dumps([None, f"连接失败 {e},同步终止"]))
            return
        remoteGallery = sorted(
            [
                remoteDownloadData[x]
                for x in remoteDownloadData
                if int(x) not in self.db.download
            ],  # json不能存储int作为key
            key=lambda item: remoteDownloadData[str(item["gid"])]["index"],
            reverse=True,
        )
        await notify(json.dumps([remoteGallery, None]))
        # 通知前端画廊列表
        # 要求前端返回需要同步的index范围 start end
        try:
            start, end = json.loads((await recv()))
            assert start >= 0 and end <= len(remoteGallery) and start <= end
        except Exception as e:
            await notify(json.dumps([None, f"参数错误 {e},同步终止"]))
            return
        # 开始同步
        # start -> end 最新到最旧 index从大到小
        # 添加下载时候 从最旧到最新添加 保持排序相同
        # 所以syncGidList从旧到新 顺序处理即可
        syncList = remoteGallery[start:end][::-1]
        splitted = [syncList[i : i + 25] for i in range(0, len(syncList), 25)]
        taskList = []
        for syncList_x25 in splitted:
            gid_token_list = [[x["gid"], x["token"]] for x in syncList_x25]
            try:
                for g_data in await self.fetchG_dataOfficial(gid_token_list):
                    taskList.append([g_data["gid"], g_data["token"], -1])  # -1代表封面
                    for i in range(int(g_data["filecount"])):
                        taskList.append(
                            [g_data["gid"], g_data["token"], i + 1]
                        )  # 从1开始
            except Exception as e:
                logger.error("请求G_DATA时发送错误" + str(e))
                await notify(json.dumps([None, "请求G_DATA时发送错误,同步终止"]))
                return
        lock = asyncio.Lock()  # 用于修改taskList的锁
        totalTaskNum = len(taskList)  # 总任务数
        finished = -1  # 已完成任务数

        async def downloader():
            nonlocal finished
            while True:
                async with lock:
                    if len(taskList) == 0:
                        return
                    gid, token, index = taskList.pop(0)
                if index == -1:
                    cachePath = path_join(self.cachePath, f"{gid}_{token}.jpg")
                    targetUrl = f"{targetServerUrl}/api/cover/{gid}_{token}.jpg"
                else:
                    cachePath = path_join(
                        self.cachePath, f"{gid}_{token}_{index:08d}.jpg"
                    )
                    targetUrl = (
                        f"{targetServerUrl}/api/Gallery/{gid}_{token}/{index:08d}.jpg"
                    )
                if not checkImg(cachePath):
                    try:
                        await self.downloadImg(
                            url=targetUrl,
                            filePath=cachePath,
                        )
                    except Exception as e:  # 出错忽略
                        logger.error(f"下载图片时出错 {e}")
                async with lock:
                    current = 100 * (totalTaskNum - len(taskList)) // totalTaskNum
                # logger.info(f"download {gid}_{token}_{index:08d}.jpg")
                if current > finished:
                    finished = current
                    logger.info(f"syncing... {current}%")
                    await notify(json.dumps([current, None]))
                    await asyncio.sleep(0.001)

        await asyncio.gather(*[downloader() for _ in range(5)])  # 并发下载
        logger.info("sync finished")
        await notify(json.dumps(["finish", None]))
        for gallery in syncList:
            logger.info(f"add download {gallery}")
            self.loop.create_task(
                self.downloadManagerInstance.addDownload(
                    gid=int(gallery["gid"]), token=gallery["token"], g_data=None
                )
            )

    async def getCardInfo(self, gid: int, token: str):
        if self.cache_cardInfo.has(gid):
            cachedCard = self.cache_cardInfo.get(gid)
            return {
                "gid": gid,
                "token": token,
                "name": cachedCard["name"],
                "rank": cachedCard["rank"],
                "category": cachedCard["category"],
                "uploadTime": cachedCard["uploadTime"],
                "lang": cachedCard["lang"],
                "pages": cachedCard["pages"],
            }
        if gid in self.db.card_info:
            # 创建一个新的字典，防止修改原字典
            return {k: v for k, v in self.db.card_info[gid].items()}
        if gid in self.db.history:
            return {k: v for k, v in self.db.history[gid].items()}
        try:
            g_data = await self.get_G_data(gid, token, cache=True, countOnly=False)
            logger.debug(f"get cardInfo ({gid}, {token}) from get_G_data")
            return {
                "gid": g_data["gid"],
                "token": g_data["token"],
                "name": g_data["title_jpn"] or g_data["title"],
                "category": g_data["category"],
                "uploadTime": time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(int(g_data["posted"]))
                ),
                "lang": "chinese" if "language:chinese" in g_data["tags"] else "",
                "rank": g_data["rating"],
                "pages": int(g_data["filecount"]),
            }
        except Exception as e:
            logger.error(f"get cardInfo ({gid}, {token}) failed")
            raise makeTrackableException(e, "get cardInfo failed")

    async def addHistory(self, gid: int, token: str):  # 添加历史记录
        cardInfo = await self.getCardInfo(gid, token)
        cardInfo["timestamp"] = int(time.time())
        self.db.history[gid] = cardInfo
        return True

    def getHistory(self):
        return sorted(
            self.db.history.values(), key=lambda x: x["timestamp"], reverse=True
        )

    def clearHistory(self) -> int:
        count = len(self.db.history.keys())
        for key in [x for x in self.db.history]:
            del self.db.history[key]
        return count

    async def makePDF(self, gid: int, token: str) -> BytesIO:
        g_data = await self.get_G_data(gid, token, True, True)
        imgList = []
        for i in range(int(g_data["filecount"])):
            imgList.append(
                await self.getGalleryImage(gid=gid, token=token, index=i + 1)
            )
        return img2pdf(imgList)
