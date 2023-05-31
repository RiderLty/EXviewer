import { getSetting } from "../utils/SettingHooks"
import { notifyMessage } from "../utils/PopoverNotifier"
import syncedDB, { FAVORITE_STATE } from "../utils/mobxSyncedState"


//封装了所有与服务器交互的api

const fix8 = (num) => (Array(8).join(0) + num).slice(-8)
const sleep = (ms) => new Promise((resolve) => {
    setTimeout(resolve, ms)
})

const notifyError = (error) => {
    notifyMessage("error", error)
}

const notifySuccess = (msg) => {
    notifyMessage("success", msg)
}

const apiUrlJoin = (path) => {
    const customApiUrl = getSetting("服务器URL", "")
    if (customApiUrl === "") {
        return path
    } else {
        return new URL(path, customApiUrl).toString()
    }
}


const Get = async (url) => {
    try {
        const response = await fetch(apiUrlJoin(url), {
            method: "GET",
            mode: "cors",
        });
        if (response.ok) {
            return [await response.json(), null];
        } else {
            const text = await response.text()
            try {
                const info = JSON.parse(text)
                return [null, JSON.parse(info.detail)];
            } catch (error) {
                return [null, [text]];
            }
        }
    } catch (error) {
        return [null, [error.toString()]];
    }
}

const Post = async (url, json) => {
    try {
        const response = await fetch(apiUrlJoin(url), {
            method: "POST",
            mode: "cors",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(json),
        })
        if (response.ok) {
            return [await response.json(), null];
        } else {
            const text = await response.text()
            try {
                const info = JSON.parse(text)
                return [null, JSON.parse(info.detail)];
            } catch (error) {
                return [null, [text]];
            }
        }
    } catch (error) {
        return [null, [error.toString()]];
    }

}


const fetchWithoutCallback = async (url) => {
    const [result, error] = await Get(url)
    if (error) {
        notifyError(error)
    } else {
        notifySuccess([result.msg])
    }
}


const fetchSilently = async (url) => {
    const [result, error] = await Get(url)
    if (error) {
        notifyError(error)
    }
}

const addFavorite = async (gid, token, index) => {
    fetchWithoutCallback(`api/addFavorite/${gid}/${token}/${index}`)
}

const removeFavorite = async (gid, token) => {
    fetchWithoutCallback(`api/rmFavorite/${gid}/${token}`)
}

const downloadGallery = async (gid, token) => {
    fetchWithoutCallback(`api/download/${gid}/${token}`)
    if (getSetting("下载时添加收藏", false)) {
        if (syncedDB.favorite[gid] && syncedDB.favorite[gid]["state"] === FAVORITE_STATE.FAVORITED) {
            return//已收藏 则返回
        } else {
            const defaultIndex = getSetting("收藏夹", 9)
            addFavorite(gid, token, defaultIndex)
        }
    }
}

const deleteGallery = async (gid, token) => {
    fetchWithoutCallback(`api/delete/${gid}/${token}`)
    if (getSetting("删除时移除收藏", false)) {
        if (syncedDB.favorite[gid] && syncedDB.favorite[gid]["state"] !== FAVORITE_STATE.NOT_FAVORITED) {
            removeFavorite(gid, token)//已收藏 才能删除
        }
    }
}

const continueDownload = async () => {
    fetchWithoutCallback(`api/continueDownload`)
}


const rateGallery = async (gid, token, score) => {
    const [result, error] = await Get(`api/rateGallery/${gid}/${token}/${score}`)
    if (error) {
        notifyError(error)
    }
    return [result, error]
}


const voteComment = async (gid, token, commentId, vote) => {
    const [result, error] = await Get(`api/voteComment/${gid}/${token}/${commentId}/${vote}`)
    if (error) {
        notifyError(error)
    }
    return [result, error]
}

const postComment = async (gid, token, content, edit, commentID) => {
    const [result, error] = await Post("api/postComment", {
        "gid": gid,
        "token": token,
        "content": content,
        "edit": edit,
        "commentID": commentID
    })
    if (error) {
        notifyError(error)
    }
    return [result, error]
}


const fetchG_Data = async (gid, token, cache, countOnly) => {
    return await Get(`api/Gallery/${gid}_${token}/g_data.json?cache=${cache}&countOnly=${countOnly}`)
}

const fetchComment = async (gid, token, all) => {
    return await Get(`api/comments/${gid}/${token}${all ? "?fetchAll=true" : ""}`)
}

const fetchDiskCacheSize = async () => {
    return await Get(`api/getDiskCacheSize`)
}

const requestClearDiskCache = async () => {
    return await Get(`api/clearDiskCache`)
}

const fetchGalleryList = async (apiURL, next) => {
    if (next) {
        return await Get(`api/${apiURL}?1=1&next=${next}`)
    } else {
        return await Get(`api/${apiURL}`)
    }
}


const getPreviewImgUrl = (gid, token, index) => {
    return apiUrlJoin(`api/preview/${gid}/${token}/${index}`)
}

const getCoverUrl = (gid, token) => {
    return apiUrlJoin(`api/cover/${gid}_${token}.jpg`)
}

const getGalleryImgUrl = (gid, token, index) => {
    return apiUrlJoin(`api/Gallery/${gid}_${token}/${fix8(index)}.jpg`)
}

const addHistory = (gid, token) => {
    fetchSilently(`api/history/add?gid=${gid}&token=${token}`)
}

const clearHistory = async () => {
    return await Get(`api/history/clear`)
}

const getWsUrl = (source) => {//获取ws链接
    if (getSetting("服务器URL", "") === "") {
        return window.location.href
            .replace(window.location.hash, "")
            .replace("https:", "wss:")
            .replace("http:", "ws:")
            .replace("3000", "7964")
            +
            source
    } else {
        return apiUrlJoin(source)
            .replace("https:", "wss:")
            .replace("http:", "ws:")
    }
}

const requestDeleteOldGallery = async () => {
    return await Get(`/api/deleteOldGallery`)
}

export {
    addFavorite,
    removeFavorite,

    downloadGallery,
    deleteGallery,
    continueDownload,

    rateGallery,

    voteComment,
    postComment,


    fetchG_Data,
    fetchComment,

    fetchDiskCacheSize,
    requestClearDiskCache,

    fetchGalleryList,

    getPreviewImgUrl,
    getCoverUrl,
    getGalleryImgUrl,

    getWsUrl,

    requestDeleteOldGallery,

    addHistory,
    clearHistory,
}