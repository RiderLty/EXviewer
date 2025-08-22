import json
import os
import subprocess
import threading
import zipfile
import time
import hashlib
import shutil
# ZIP_TMP_DIR = r"P:\\"
# REMOTE_PATH = "onedrive:/EHBackups"
# DB_PATH = r"E:\EHDownloads\api\NosqlDB.json"
# GALLERY_PATH = r"E:\EHDownloads\Gallery"
# COVER_PATH = r"E:\EHDownloads\cover"
# REMOTE_PATH = "onedrive:/EHBackups"


# ZIP_TMP_DIR = r"/mnt/ramdisk"
ZIP_TMP_DIR = r"/mnt/massiveStorage/EHBackups/tmp"
DB_PATH = r"/mnt/storage/Exviewer/EHDownloads/api/NosqlDB.json"
GALLERY_PATH = r"/mnt/storage/Exviewer/EHDownloads/Gallery"
COVER_PATH = r"/mnt/storage/Exviewer/EHDownloads/cover"
REMOTE_PATH = r"/mnt/massiveStorage/EHBackups/manual"


def hash_gallery(gid_token):
    return str(int(hashlib.md5(gid_token.encode()).hexdigest(), 16) % 64 + 1)


def zipDir(dirpath, outputAbsPath):
    """
    压缩指定文件夹
    :param dirpath: 目标文件夹路径
    :param outputAbsPath: 压缩文件保存绝对路径
    :return: None
    """
    dirname = dirpath.split("/")[-1]
    zipItem = zipfile.ZipFile(outputAbsPath, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
        fpath = path.replace(dirpath, "")
        for filename in filenames:
            zipItem.write(
                os.path.join(path, filename),
                os.path.join(dirname + "/" + fpath, filename),
            )
    zipItem.close()


def uploader(gallery: str, sem: threading.Semaphore):  # abs path of gallery
    gid_token = os.path.split(gallery)[1]
    tmpZipPath = os.path.join(ZIP_TMP_DIR, gid_token + ".zip")
    zipDir(gallery, tmpZipPath)  # 直接覆盖
    # res = execute(f"rclone copy {tmpZipPath} {REMOTE_PATH}/Gallery/{hash_gallery(gid_token)}")
    
    os.makedirs(os.path.join(REMOTE_PATH, "Gallery", hash_gallery(gid_token)), exist_ok=True)
    shutil.copy(tmpZipPath, os.path.join(REMOTE_PATH, "Gallery", hash_gallery(gid_token), f"{gid_token}.zip"))
    print(f"uploaded {gid_token} to {REMOTE_PATH}/Gallery/{hash_gallery(gid_token)}/{gid_token}.zip")
    os.remove(tmpZipPath)
    sem.release()


def deleter(gid_token: str, sem: threading.Semaphore):
    start = time.perf_counter()
    os.remove(f"{REMOTE_PATH}/Gallery/{hash_gallery(gid_token)}/{gid_token}.zip")
    sem.release()


if __name__ == "__main__":
    print("uploading DB")
    start = time.perf_counter()
    res = os.system(f"rclone copy {DB_PATH} {REMOTE_PATH} ")
    shutil.copy(DB_PATH, os.path.join(REMOTE_PATH, "NosqlDB.json"))
    print("over", time.perf_counter() - start)
    print("listing remote",  f"rclone lsjson  --files-only --max-depth 2 {REMOTE_PATH}/Gallery")
    
    
    uploadedList = []

    files = os.walk(os.path.join(REMOTE_PATH, "Gallery"))
    print("remote files:")
    for root, dirs, files in files:
        for file in files:
            print(file)
            uploadedList.append(file.split(".zip")[0]) 

    print("远程已存在 {}".format(len(uploadedList)))

    needUploadList = [
        os.path.join(GALLERY_PATH, gid_token)
        for gid_token in os.listdir(GALLERY_PATH)
        if gid_token not in uploadedList
    ]
    print("need upload {}".format(len(needUploadList)))
    local = os.listdir(GALLERY_PATH)
    needDeleteGTList = [
        gid_token
        for gid_token in uploadedList
        if gid_token not in local
    ]

    print("need delete {}".format(len(needDeleteGTList)))
    del_sem = threading.Semaphore(1)
    for gid_token in needDeleteGTList:
        del_sem.acquire()
        threading.Thread(target=deleter, args=(gid_token, del_sem)).start()

    [del_sem.acquire() for _ in range(1)]

    upl_sem = threading.Semaphore(1)
    for gallery in needUploadList:
        upl_sem.acquire()
        threading.Thread(target=uploader, args=(gallery, upl_sem)).start()

    [upl_sem.acquire() for _ in range(1)]
    print("upload over")
    print("uploading cover")
    # os.system(f"rclone sync D:\EHDownloads\cover {REMOTE_PATH}\cover -P --transfers=32")
    # rclone sync F:\EHBackups aliyunenc:EHBackups -P --dry-run
    # rclone sync F:\EHBackups onedrive:EHBackups -P --dry-run
