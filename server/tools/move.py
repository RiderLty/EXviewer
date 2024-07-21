import json
import os
import shutil
import hashlib
import subprocess

def hash_gallery(gid_token):
    return str(int(hashlib.md5(gid_token.encode()).hexdigest(), 16) % 64 + 1)



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
    
    
# for file in os.listdir(r"W:\EHBackups\Gallery"):
#     if file.endswith(".zip"):
#         d = hash_gallery(file.split(".")[0])
        
#         print(file.split(".")[0] , d)


res = execute("rclone lsjson  --files-only --max-depth 2 W:\EHBackups\Gallery")
for item in json.loads(res["out"]):
    # print(item["Name"] , item["Name"].split(".")[0] , hash_gallery(item["Name"].split(".")[0]) )
    src = os.path.join("W:\EHBackups\Gallery", item["Path"].replace("/","\\"))
    dst = os.path.join("W:\EHBackups\Gallery", hash_gallery(item["Name"].split(".")[0]), item["Name"] )
    if src != dst:
        print(src,dst)
            # os.makedirs(os.path.join("W:\EHBackups\Gallery", d),exist_ok=True)
        try:
            shutil.move(src , dst)
        except Exception:
            pass
       