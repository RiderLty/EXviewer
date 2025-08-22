import json
from time import sleep
from tinydb import TinyDB
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage
from PIL import Image

import requests
import os

NOSQL_DB = r"/mnt/storage/Exviewer/EHDownloads/api/NosqlDB.json"
SCAN_MODE = 2# 检查下载完整性 0仅检查文件夹是否存在 1检查文件夹和文件列表 2检查文件夹内图片完整性
GALLERY_DOWNLOAD_PATH = r"/mnt/storage/Exviewer/EHDownloads/Gallery"
COVER_DOWNLOAD_PATH = r"/mnt/storage/Exviewer/EHDownloads/cover"
CHECK_LOG = r"/mnt/storage/Projects/exviewer/server/tools/checkPassed.json"
GALLERY_DOWNLOAD_FILES = set(os.listdir(GALLERY_DOWNLOAD_PATH))
COVER_DOWNLOAD_FILES = set(os.listdir(COVER_DOWNLOAD_PATH))

SUCCESS = "成功"
DIR_NOT_EXIST = "文件夹不存在"
G_DATA_NOT_EXIST = "g_data.json缺失"
IMG_LOSS = "图片文件缺失"
IMG_CHECK_FAIL = "图片完整性检测不通过"

def checkGallery(gid_token,fileCount = 0):
    gallery_path = os.path.join(GALLERY_DOWNLOAD_PATH,gid_token)
    if gid_token not in GALLERY_DOWNLOAD_FILES:
        return DIR_NOT_EXIST
    if SCAN_MODE == 0:
        return SUCCESS
    files = os.listdir(gallery_path)
    if "g_data.json" not in files:
        return G_DATA_NOT_EXIST
    
    flag = True
    for i in range(fileCount):
        if f"{(i+1):08d}.jpg" not in files:
            img_path = os.path.join(gallery_path,f"{(i+1):08d}.jpg")
            print(f"{img_path} lost in {gid_token}")
            flag = False

    if not flag:
        return IMG_LOSS
    if SCAN_MODE == 1:
        return SUCCESS
    flag = True
    for i in range(fileCount):
        img_path = os.path.join(gallery_path,f"{(i+1):08d}.jpg")
        try:
            Image.open(img_path).verify()
        except Exception as e:
            print(f"{img_path} verify failed in {gid_token}")
            flag = False
    if not flag:
        return IMG_CHECK_FAIL
    return SUCCESS

def printUrl(gid_token):
    gid,token = gid_token.split("_")
    print(f"http://localhost:7964/#/g/{gid}/{token}")

if __name__ == "__main__":
    dataDB = TinyDB(NOSQL_DB, storage=CachingMiddleware(JSONStorage))
    g_data_table = dataDB.table("g_data")
    download_table = dataDB.table("download")

    download_gidList = set([f'{x["gid"]}_{x["token"]}' for x in download_table.all()])
    g_data_gidList = set([f'{x["gid"]}_{x["token"]}' for x in g_data_table.all()])

    no_g_data_download_rec = [x for x in download_gidList if x not in g_data_gidList]
    no_download_rec_g_data = [x for x in g_data_gidList if x not in download_gidList]

    print("有下载记录 但是没g_data的")
    for gid_token in  no_g_data_download_rec:
        printUrl(gid_token)
    print("="*40)
    print("存储了g_data 却没有下载的")
    for gid_token in no_download_rec_g_data:
        printUrl(gid_token)
    print("="*40)

    if len(no_g_data_download_rec) != 0 or len(no_download_rec_g_data) != 0:
        exit(1)

    history_check = set(json.load(open(CHECK_LOG,'r')))#全扫描很耗时 因此只扫描一次
    current_check = []
    count = 0
    total = len(g_data_table.all())
    for g_data in g_data_table.all():
        count += 1
        gid_token = f'{g_data["gid"]}_{g_data["token"]}'
        if gid_token in history_check:
            print(f"{gid_token} pass {count}/{total}",end="\r")
            current_check.append(gid_token)
            continue
        fileCount = int(g_data["filecount"])
        res = checkGallery(gid_token,fileCount)
        if res != SUCCESS:
            printUrl(gid_token)
            print(res) 
            print("")
        else:
            print(f"{gid_token} {res} {count}/{total}",end="\r")
            current_check.append(gid_token)
    json.dump(current_check,open(CHECK_LOG,'w'))

    print("\n","="*40)


    g_data_cover = set([
        f'{x["gid"]}_{x["token"]}.jpg' for x in g_data_table.all() 
    ])


    cover_not_download = [x for x in g_data_cover if x not in COVER_DOWNLOAD_FILES]
    cover_not_need = [x for x in COVER_DOWNLOAD_FILES if x not in g_data_cover]
    print("缺失的封面")
    for cover in  cover_not_download:
        print(cover)
    print("="*40)
    print("多余的封面")
    for cover in cover_not_need:
        print(cover)
        # os.remove(os.path.join(COVER_DOWNLOAD_PATH,cover))
    print("="*40)