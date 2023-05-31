import json
import os
import subprocess
import threading
import zipfile
import time

ZIP_TMP_DIR = r"P:\\"
REMOTE_PATH = "onedrive:/EHBackups"
DB_PATH = r"D:\EHDownloads\api\NosqlDB.json"
GALLERY_PATH = r"D:\EHDownloads\Gallery"
COVER_PATH = r"D:\EHDownloads\cover"

def execute(command_with_args):
    try:
        with subprocess.Popen(
            command_with_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as proc:
            (out, err) = proc.communicate()
            return {"code": proc.returncode, "out": out.decode("utf-8").replace("\\n", "\n"), "error": err}
    except FileNotFoundError as not_found_e:
        return {"code": -20, "error": not_found_e}
    except Exception as generic_e:
        return {"code": -30, "error": generic_e}


def zipDir(dirpath, outputAbsPath):
    """
    压缩指定文件夹
    :param dirpath: 目标文件夹路径
    :param outputAbsPath: 压缩文件保存绝对路径
    :return: None
    """
    dirname = dirpath.split("\\")[-1]
    zipItem = zipfile.ZipFile(outputAbsPath, "w", zipfile.ZIP_DEFLATED)
    for path, dirnames, filenames in os.walk(dirpath):
        # 去掉目标跟路径，只对目标文件夹下边的文件及文件夹进行压缩
        fpath = path.replace(dirpath, "")
        for filename in filenames:
            zipItem.write(
                os.path.join(path, filename),
                os.path.join(dirname + "\\" + fpath, filename),
            )
    zipItem.close()


def uploader(gallery: str, sem: threading.Semaphore):  # abs path of gallery
    gid_token = os.path.split(gallery)[1]
    tmpZipPath = os.path.join(ZIP_TMP_DIR, gid_token + ".zip")
    zipDir(gallery, tmpZipPath)  # 直接覆盖
    res = execute("rclone copy {} {}/Gallery".format(tmpZipPath, REMOTE_PATH))
    if res["code"] == 0:
        print(f"success {gid_token}")
    else:
        print(res)
    os.remove(tmpZipPath)
    sem.release()


def deleter(gid_token: str, sem: threading.Semaphore):
    start = time.perf_counter()
    res = execute(f"rclone deletefile {REMOTE_PATH}/Gallery/{gid_token}.zip")
    print(gid_token, "delete over", time.perf_counter() - start)
    if res["code"] != 0:
        print(res)
    sem.release()


if __name__ == "__main__":
    print("uploading DB")
    start = time.perf_counter()
    res = execute(f"rclone copy {DB_PATH} {REMOTE_PATH} ")
    print("over", time.perf_counter() - start)
    if res["code"] != 0:
        print(res)
        exit(1)
    print("listing remote")
    start = time.perf_counter()
    res = execute(f"rclone lsjson {REMOTE_PATH}/Gallery")
    print("over", time.perf_counter() - start)
    if res["code"] != 0:
        print(res)
        exit(1)
    uploadedList = [item["Name"].split(".")[0]
                    for item in json.loads(res["out"])]

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
    del_sem = threading.Semaphore(16)
    for gid_token in needDeleteGTList:
        del_sem.acquire()
        threading.Thread(target=deleter, args=(gid_token, del_sem)).start()

    [del_sem.acquire() for _ in range(16)]

    upl_sem = threading.Semaphore(5)
    for gallery in needUploadList:
        upl_sem.acquire()
        threading.Thread(target=uploader, args=(gallery, upl_sem)).start()

    [upl_sem.acquire() for _ in range(5)]
    print("upload over")
    print("uploading cover")
    os.system("rclone sync D:\EHDownloads\cover onedrive:EHBackups\cover -P --transfers=32")