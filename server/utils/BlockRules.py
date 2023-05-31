from fastapi import Request
from IPy import IP


def getRulesChecker(rule):
    if rule["TYPE"] == "WHITE_LIST":
        ipList = [IP(item) for item in rule["WHITE_LIST"]]
        def checkBlock(request: Request):  # if blocked return true
            for ip in ipList:
                if request.client.host in ip:
                    return False
            return True

    elif rule["TYPE"] == "BLACK_LIST":
        ipList = [IP(item) for item in rule["BLACK_LIST"]]
        def checkBlock(request: Request):  # if blocked return true
            for ip in ipList:
                if request.client.host in ip:
                    return True
            return False
    else:
        def checkBlock(request: Request):
            return False
    return checkBlock
