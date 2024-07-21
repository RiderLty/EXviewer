import asyncio
import json
import os
import shutil
from typing import List

from utils.DBM import DOWNLOAD_STATE
from utils.tools import checkImg, logger, printTrackableException

SIGNAL_SUCCESS = 0
SIGNAL_FAILURE = 1
SIGNAL_INTERRUPT = 2


class worker():
    def __init__(self, aioAccessorInstance, loop: asyncio.AbstractEventLoop, gid: int, token: str, g_data=None) -> None:
        self.aioAccessorInstance = aioAccessorInstance
        self.loop = loop
        self.gid = gid
        self.token = token
        self.g_data = g_data
        self.interrupted = False
        self.running = False
        self.channel = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.imgPathMap = {}
        self.fileCount = 0
        self.coverPath = ""
        self.noLocalImageIndexList = []

    def getDownloadedCount(self):
        # 获取需要下载的index
        # 应因为下载失败时候继续下载也是addDownload
        # 避免出现短时间大量通信以减少前端运算量
        for index in range(self.fileCount):
            localImg = self.aioAccessorInstance.checkGalleryImageLocal(self.gid, self.token, index + 1)
            if localImg != None:
                if checkImg(localImg):
                    self.imgPathMap[index] = localImg
                else:
                    os.path.exists(localImg) and os.remove(localImg)
                    self.noLocalImageIndexList.append(index)          
            else:
                self.noLocalImageIndexList.append(index)
        return self.fileCount - len(self.noLocalImageIndexList)

    def match(self, gid: int, token: str):
        return self.gid == gid and self.token == token

    async def mainLoop(self):
        async with self.lock:
            self.running = True
            success = 0
            try:
                if self.g_data == None:
                    fetch_g_data = self.aioAccessorInstance.fetchG_dataOfficial(
                        [(self.gid, self.token)])
                    fetch_cover = self.aioAccessorInstance.getGalleryCover(
                        self.gid, self.token)
                    g_data_list, coverPath = await asyncio.gather(fetch_g_data, fetch_cover)
                    self.g_data = g_data_list[0]
                    self.coverPath = coverPath
                else:
                    self.coverPath = await self.aioAccessorInstance.getGalleryCover(self.gid, self.token)
                logger.debug(
                    f"下载中 G_data : \n{json.dumps(self.g_data,indent=4,ensure_ascii=False)}")
                logger.debug(f"下载中 cover : {self.coverPath}")
                # 更新card_info 因为添加下载的时候出错也无视 这里有g_data 就一定可以更新
                await self.aioAccessorInstance.updateCardInfo(self.gid, self.token)
                self.aioAccessorInstance.db.g_data[self.gid] = self.g_data
                self.fileCount = int(self.g_data["filecount"])
                # 尝试复用
                await self.aioAccessorInstance.parentImgMultiplex(self.gid, self.token)
                success = self.getDownloadedCount()
                self.aioAccessorInstance.db.download[self.gid]['success'] = success
            except Exception as e:
                logger.error(str(e))
                logger.error(f"下载任务已终止  {self.gid}_{self.token}")
                if self.aioAccessorInstance.db.download[self.gid]:
                    self.aioAccessorInstance.db.download[self.gid]['state']=DOWNLOAD_STATE.FINISHED
                return
            self.aioAccessorInstance.db.download[self.gid]['state'] = DOWNLOAD_STATE.NOW_DOWNLOADING

            self.downloader()

            for _ in range(self.fileCount - success):
                signal = await self.channel.get()
                if signal == SIGNAL_SUCCESS:
                    success += 1
                    if self.aioAccessorInstance.db.download[self.gid]:
                        self.aioAccessorInstance.db.download[self.gid]['success'] = success
                elif signal == SIGNAL_FAILURE:
                    pass
                elif signal == SIGNAL_INTERRUPT:
                    logger.warning(
                        f"图片下载已撤销 {self.gid}_{self.token}:{json.dumps(self.noLocalImageIndexList)}")
                    # if self.aioAccessorInstance.db.download[self.gid]:
                    #     self.aioAccessorInstance.db.download[self.gid]['state'] = DOWNLOAD_STATE.FINISHED
                    return

            if self.aioAccessorInstance.db.download[self.gid]:
                self.aioAccessorInstance.db.download[self.gid]['state'] = DOWNLOAD_STATE.FINISHED

            if success == self.fileCount:
                try:
                    saveDir = os.path.join(
                        self.aioAccessorInstance.galleryPath, f"{self.gid}_{self.token}")
                    if not os.path.exists(saveDir):
                        os.makedirs(saveDir)
                    for i in range(self.fileCount):
                        dst = os.path.join(saveDir, f"{(i + 1):08d}.jpg")
                        src = self.imgPathMap[i]         
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                            logger.debug(f"mv {src} -> {dst}")
                    g_data_json_save_path = os.path.join(
                        saveDir, "g_data.json")
                    with open(g_data_json_save_path, "w", encoding="utf-8") as f:
                        json.dump(self.g_data, f, ensure_ascii=True, indent=4)
                    logger.debug(f"保存 g_data.json 到 {g_data_json_save_path}")
                    cover_save_path = os.path.join(
                        self.aioAccessorInstance.coverPath, f"{self.gid}_{self.token}.jpg")
                    shutil.move(self.coverPath, cover_save_path) if not os.path.exists(
                        cover_save_path) else None
                    logger.debug(f"mv {self.coverPath} -> {cover_save_path}")
                    logger.info(f"{self.gid}_{self.token} 下载完成")
                except Exception as e:
                    logger.error(f"{self.gid}_{self.token} 后续处理错误 {e}")
                    if self.aioAccessorInstance.db.download[self.gid]:
                        self.aioAccessorInstance.db.download[self.gid]['success'] = 0
                        self.aioAccessorInstance.db.download[self.gid]['state'] = DOWNLOAD_STATE.FINISHED
                    return
            else:
                logger.warning(
                    f"{self.gid}_{self.token} 下载失败 {success}/{self.fileCount}")

    def downloader(self):
        taskLock = asyncio.Lock()

        async def downloadFunc():
            while True:
                async with taskLock:
                    if len(self.noLocalImageIndexList) == 0:
                        return
                    index = self.noLocalImageIndexList.pop(0)
                if not self.interrupted:
                    try:
                        imgPath = await self.aioAccessorInstance.getGalleryImage(self.gid, self.token, index+1)                        
                        self.imgPathMap[index] = imgPath
                        await asyncio.sleep(1/1000)
                        await self.channel.put(SIGNAL_SUCCESS)
                        logger.debug(f"图片下载成功 {self.gid}_{self.token} {index}")
                    except Exception as e:
                        printTrackableException(e)
                        await self.channel.put(SIGNAL_FAILURE)
                        logger.warning(
                            f"图片下载失败 {self.gid}_{self.token}/{index}")
                else:
                    return
        [self.loop.create_task(downloadFunc()) for _ in range(5)]

    async def interrupt(self,):
        self.interrupted = True
        if self.running:
            await self.channel.put(SIGNAL_INTERRUPT)

    async def deleteGallery(self,):
        logger.warning(f"deleteGallery{self.gid}{self.token}")
        saveDir = os.path.join(
            self.aioAccessorInstance.galleryPath, f"{self.gid}_{self.token}")
        cover_save_path = os.path.join(
            self.aioAccessorInstance.coverPath, f"{self.gid}_{self.token}.jpg")
        async with self.lock:
            if self.aioAccessorInstance.db.download[self.gid] != None:
                del self.aioAccessorInstance.db.download[self.gid]
                logger.warning(f"删除download记录 {self.gid}")
            if self.aioAccessorInstance.db.g_data[self.gid] != None:
                del self.aioAccessorInstance.db.g_data[self.gid]
                logger.warning(f"删除g_data记录 {self.gid}")
            if self.aioAccessorInstance.db.card_info[self.gid]:
                del self.aioAccessorInstance.db.card_info[self.gid]
                logger.warning(f"删除card_info记录 {self.gid}")
            if os.path.exists(saveDir):
                logger.warning(f"删除 {saveDir}")
                shutil.rmtree(saveDir)
            if os.path.exists(cover_save_path):
                logger.warning(f"删除 {cover_save_path}")
                os.remove(cover_save_path)


class downloadManager():
    def __init__(self, aioAccessorInstance) -> None:
        self.aioAccessorInstance = aioAccessorInstance
        self.loop = aioAccessorInstance.loop
        self.wrLock = asyncio.Lock()
        self.workingWorker = None
        self.workerQueue = asyncio.Queue()  # loop=self.loop
        self.workers: List[worker] = []
        self.workersCountSem = asyncio.Semaphore(0,)  # loop=self.loop
        self.simulateFunctionCall = asyncio.Queue()  # loop=self.loop

        # 等待信号量
        # 取出第一个worker
        # 执行mainLoop与startWorker
        # 等待结束
        # 从队列中删除worker
        async def asyncLoop():
            while True:
                await self.workersCountSem.acquire()
                async with self.wrLock:
                    worker = self.workers[0]  # 拿到一个worker
                await worker.mainLoop()
                async with self.wrLock:
                    self.workers.pop(0)  # 删除worker
        self.loop.create_task(asyncLoop())

    async def addDownload(self, gid: int, token: str, g_data=None):
        # 添加一个worker到尾部
        # 信号量+1
        logger.info(f"添加下载 {gid}_{token}")
        self.loop.create_task(
            self.aioAccessorInstance.updateCardInfo(gid, token))
        async with self.wrLock:
            if self.aioAccessorInstance.db.download[gid] == None:
                self.aioAccessorInstance.db.download[gid] = {
                    'gid': gid,
                    'token': token,
                    'success': 0,
                    'state': DOWNLOAD_STATE.IN_QUEUE,
                    'index': self.aioAccessorInstance.getNowDownloadIndex()
                }
            else:
                self.aioAccessorInstance.db.download[gid]['success'] = 0
                self.aioAccessorInstance.db.download[gid]['state'] = DOWNLOAD_STATE.IN_QUEUE
            downloadWorker = worker(
                self.aioAccessorInstance, self.loop, gid, token, g_data)
            self.workers.append(downloadWorker)
            self.workersCountSem.release()

    async def deleteDownload(self, gid, token):
        # 遍历worker
        # 如果match 则执行interrupt然后执行delete
        # 否则直接创建一个worker 并执行delete
        logger.info(f"删除下载 {gid}_{token}")
        async with self.wrLock:
            inQueueWorker = False
            for workerInstance in self.workers:
                if workerInstance.match(gid, token):
                    inQueueWorker = True
                    await workerInstance.interrupt()
                    await workerInstance.deleteGallery()
        if not inQueueWorker:
            await worker(self.aioAccessorInstance, self.loop, gid, token, None).deleteGallery()
