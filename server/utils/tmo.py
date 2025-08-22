import os
import shutil
target_cache = "/mnt/storage/Exviewer_auto/Cache"
for file in os.listdir(target_cache):
    if "jpg" not in file:
        print(f"Skipping non-jpg file: {file}")
        continue
    spls = file.split("_")
    if len(spls) < 2:
        continue
    
    if len(spls) == 3:
        gid = spls[0]
        token = spls[1]
        index = spls[2].split(".")[0]
    else:
        gid = spls[0]
        token = spls[1].split(".")[0]
        index = -1
    if index == -1:
        cachePath = os.path.join(target_cache, "cover", f"{gid}_{token}.jpg")
        parentDir = os.path.dirname(cachePath)
        if not os.path.exists(parentDir):
            os.makedirs(parentDir, exist_ok=True)
        shutil.move(os.path.join(target_cache, file), cachePath) 
    else:
        cachePath = os.path.join(target_cache, f"{gid}_{token}", f"{index}.jpg")
        parentDir = os.path.dirname(cachePath)
        if not os.path.exists(parentDir):
            os.makedirs(parentDir, exist_ok=True)
        shutil.move(os.path.join(target_cache, file), cachePath)