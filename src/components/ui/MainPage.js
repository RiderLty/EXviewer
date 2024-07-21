
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import CachedIcon from '@mui/icons-material/Cached';
import DownloadIcon from '@mui/icons-material/Download';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import FileDownloadOffIcon from '@mui/icons-material/FileDownloadOff';
import HomeIcon from '@mui/icons-material/Home';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import LogoDevIcon from '@mui/icons-material/LogoDev';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SettingsIcon from '@mui/icons-material/Settings';
import ShuffleIcon from '@mui/icons-material/Shuffle';
import SortByAlphaIcon from '@mui/icons-material/SortByAlpha';
import SubscriptionsIcon from '@mui/icons-material/Subscriptions';
import KeyboardDoubleArrowRight from '@mui/icons-material/KeyboardDoubleArrowRight'
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router';
import FloatSpeedDial from './MainPageComponents/FloatSpeedDial';
import LeftMenu from './MainPageComponents/LeftMenu';
import LongClickMenu from './MainPageComponents/LongClickMenu';
import TopSearchBar from './MainPageComponents/TopSearchBar';
import VScrollCardContainer from './MainPageComponents/VScrollCardContainer';
import { notifyMessage } from '../utils/PopoverNotifier';
import SecondConfirmDialog from '../utils/SecondConfirmDialog';
import JumpScroll from '../utils/JumpScroll';
import { getSetting, useSettingBind } from '../utils/SettingHooks';
import syncedDB, { DOWNLOAD_STATE } from '../utils/mobxSyncedState';
import { observer } from "mobx-react";
import { addFavorite, continueDownload, deleteGallery, downloadGallery, fetchGalleryList, removeFavorite } from '../api/serverApi';
import { autorun, toJS } from 'mobx';
import FolderZipIcon from '@mui/icons-material/FolderZip';
import { customFilter } from '../utils/tools';
import jsonpath from "jsonpath"
import TuneIcon from '@mui/icons-material/Tune';
// import { useWorker, WORKER_STATUS } from "@koale/useworker";
import { v4 as uuidGenerator } from 'uuid';
import HistoryIcon from '@mui/icons-material/History';

import LowPriorityIcon from '@mui/icons-material/LowPriority';
import UTurnRightIcon from '@mui/icons-material/UTurnRight';
import CloudSyncIcon from '@mui/icons-material/CloudSync';
import SyncIcon from '@mui/icons-material/Sync';
import DownloadingIcon from '@mui/icons-material/Downloading';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';


const listUnion = (oldState, newState) => {//合并列表 新的元素按照新列表的顺序添加到最前方
    const oldSet = new Set(oldState)
    const newSet = new Set(newState)
    const fileted = oldState.filter(item => newSet.has(item))
    const newAdd = newState.filter(item => oldSet.has(item) === false)
    return [...newAdd, ...fileted]
}


const randomSort = (arr) => {
    // console.time("randomSort")
    // const res = arr.sort(() => Math.random() - 0.5)
    // console.timeEnd("randomSort")
    // return res
    return arr.sort(() => Math.random() - 0.5)
}

const nameSort = (arr, dict) => {
    const nameDict = {}
    const firstShow = []
    for (let item of arr) {
        const hashName = dict[item].name.replace(/\[.*?\]|\(.*?\)|【.*?】|（.*?）|\s+/g, "")
        if (nameDict[hashName] !== undefined) {
            if (dict[item].lang === "chinese") {
                //如果是中文画廊，则放在前面
                nameDict[hashName].unshift(item)
            } else {
                //其他语言画廊，则放在后面
                nameDict[hashName].push(item)
            }
        } else {
            nameDict[hashName] = [item]
        }
        if (firstShow.indexOf(hashName) === -1) {
            firstShow.push(hashName)
        }
    }
    const newList = []
    for (let hashName of firstShow) {
        newList.push(...nameDict[hashName])
    }
    return newList
}

const mergeAndDistinct = (arr1, arr2) => {//arr1 和 arr2 不去重
    const arr1Set = new Set(arr1)
    return [...arr1,
    ...arr2.filter(item => !arr1Set.has(item))
    ]
}

export const leftMenuMap = {
    "自定义": "/userFilter",
    "主页": "/",
    "订阅": "/watched",
    "热门": "/popular",
    "收藏": "/favorites",
    "下载": "/downloaded",
    "历史": "/history",
    "导入": "/uploadZip",
    "同步": "/syncFromOther",
    "设置": "/setting",
}


function MainPage_inner(props) {

    const [cardGidList, setCardGidList] = useState([])
    const [cardInfoMap, setCardInfoMap] = useState({})
    const downloadCount = useRef(0)
    const pageNext = useRef(null)
    const requestDataLock = useRef(false)
    const [loading, setLoading] = useState(false)
    const containerUID = useRef(uuidGenerator())

    const downloadingPageCardGidList = useMemo(() => {
        return cardGidList.filter((gid) => cardInfoMap[gid] && syncedDB.download[gid] && cardInfoMap[gid].pages !== syncedDB.download[gid].success)
    }, [cardGidList])

    const syncDownloadDBToHooks = (
        forceUpdate,
        download_key_set,
        download,
        card_info
    ) => {
        if (!forceUpdate && download_key_set.size === downloadCount.current) return
        const indexedDownload = []
        Object.values(download).forEach(item => {
            indexedDownload[item.index] = item.gid// {gid,index,state,success} index不连续
        })

        const newCardList = indexedDownload.filter(gid => gid && card_info[gid]).reverse() //去除空 去除没有card_info的

        downloadCount.current = newCardList.length

        if (forceUpdate) {
            setCardInfoMap(toJS(card_info))
            setCardGidList(newCardList)
        } else {
            setCardInfoMap(toJS(card_info))
            setCardGidList((old) => listUnion(old, newCardList))
        }
    }

    const syncHistoryDBToHooks = (
        history
    ) => {
        const historyLen = getSetting("浏览历史", "100")
        const newGidList = Object.values(history).map(item => item.gid)
        const slicedList = historyLen === "无限制" ? newGidList : newGidList.slice(0, Number(historyLen))
        slicedList.sort((a, b) => {
            return history[b].timestamp - history[a].timestamp
        })
        setCardInfoMap(toJS(history))
        setCardGidList(slicedList)
    }

    const requestData = async () => {
        if (props.downloadPage) {//是下载页面 则强制mobx同步状态
            syncDownloadDBToHooks(
                true,
                toJS(syncedDB.keys.download),
                syncedDB.download,
                syncedDB.card_info
            )
            setLoading(false)
        } else if (props.pathname === "/history") {
            syncHistoryDBToHooks(
                toJS(syncedDB.history),
            )
            setLoading(false)
        } else {//否则正常请求使数据
            if (requestDataLock.current) return
            requestDataLock.current = true
            const prevProps = JSON.stringify(props)
            setLoading(true)

            if (getSetting("搜索本地画廊", false) && props.pathname === "/search" && pageNext.current === null) {
                const f_search_str = props.search.slice(0, 1) === "?" ? "&" + props.search.slice(1) : props.search
                const [searchLocalData, error] = await fetchGalleryList(`./searchLocal/?1=1${f_search_str}`, null)
                if (error) {
                    notifyMessage("error", error)
                } else {
                    const dataDict = {}
                    searchLocalData.forEach(item => { dataDict[item.gid] = item })
                    const dataGidList = searchLocalData.map(item => item.gid)
                    setCardInfoMap(prev => { return { ...prev, ...dataDict } })//合并map数据
                    setCardGidList(prev => mergeAndDistinct(prev, dataGidList))//合并列表
                }
            }

            const [rawData, error] = await fetchGalleryList(props.apiURL, pageNext.current)
            if (error) {
                notifyMessage("error", error)
                requestDataLock.current = false
                setLoading(false)
                return false
            } else {
                if (prevProps !== JSON.stringify(props)) {
                    console.log("props changed, ignore response")
                    return// 上一次请求还没完成 用户就切换路由 直接丢弃
                } else {
                    const data = props.pathname === "/userFilter" ? jsonpath.query(rawData, getSetting("自定义筛选器", "*")) : rawData
                    const dataDict = {}
                    data.forEach(item => { dataDict[item.gid] = item })//提取gid作为key 
                    const dataGidList = data.map(item => item.gid)//gid列表
                    setCardInfoMap(prev => { return { ...prev, ...dataDict } })//合并map数据
                    setCardGidList(prev => mergeAndDistinct(prev, dataGidList))//合并列表
                    if (rawData.length > 0) {
                        pageNext.current = rawData[rawData.length - 1].gid
                    }
                    requestDataLock.current = false
                    setLoading(false)
                    return true
                }
            }
        }
    }

    const initClearAll = () => {
        setLoading(false)
        requestDataLock.current = false
        setCardGidList([])
        setCardInfoMap({})
        pageNext.current = null
    }

    useEffect(() => {
        initClearAll()
        requestData()
    }, [
        props.initSearch,
        props.apiURL,
        props.downloadPage
    ])

    useEffect(() => {
        autorun(() => {
            if (props.downloadPage) {
                console.time("autorun toJS(syncedDB.keys.download)")
                const jsObject = toJS(syncedDB.keys.download)
                console.timeEnd("toJS(syncedDB.keys.download)")
                console.time("autorun 同步数据库到hooks")
                syncDownloadDBToHooks(
                    false,
                    jsObject,
                    syncedDB.download,
                    syncedDB.card_info
                )
                console.timeEnd("autorun 同步数据库到hooks")
            } else if (props.pathname === "/history") {
                syncHistoryDBToHooks(
                    toJS(syncedDB.history),
                )
            } else {

            }
        })
    }, [])

    const lastTop = useRef(0);
    const scrollTop = useRef(0)
    const [scrollControlledHidden, setScrollControlledHidden] = useState(false)
    const setScrollTop = (value) => {
        scrollTop.current = value
        if (scrollTop.current > lastTop.current) {
            setScrollControlledHidden(true)
        } else {
            setScrollControlledHidden(false)
        }
        lastTop.current = scrollTop.current;
    }

    const [refreshToken, setRefreshToken] = useState(Math.random())

    const [deleteSecondConfirm, setDeleteSecondConfirm] = useState({})
    const handelSecondConfirm = (gid, token, title) => {
        setDeleteSecondConfirm({
            title: title,
            open: true,
            onConfirm: () => {
                deleteGallery(gid, token)
                setDeleteSecondConfirm({})
            },
            handleClose: () => { setDeleteSecondConfirm({}) }
        })
    }

    const [jumpScrollOpen, setJumpScrollOpen] = useState(false)
    const handelJumpScrollOpen = () => { setJumpScrollOpen(true) }
    const handelJumpScrollClose = () => { setJumpScrollOpen(false) }

    const [leftMenuOpen, setLeftMenuOpen] = useState(false)
    const [pos, setPos] = useState([-1, -1])
    const [longClickItems, setLongClickItems] = useState([])
    const [longClickedName, setLongClickedName] = useState("")
    const [downloadingPage, setDownloadingPage] = useState(false)

    useEffect(() => {
        initClearAll()
        requestData()
    }, [downloadingPage])


    const handelLongClick = (gid, token, name, favorited, canDelete, canContinue, x, y) => {
        setLongClickItems([
            { text: "阅读", onClick: () => { props.openRead(gid, token) }, icon: <AutoStoriesIcon /> },

            canContinue ? { text: "继续下载", onClick: () => { downloadGallery(gid, token) }, icon: <FileDownloadIcon /> } : null,

            canDelete ? { text: "删除下载", onClick: () => { handelSecondConfirm(gid, token, name) }, icon: <FileDownloadOffIcon /> }
                : { text: "下载", onClick: () => { downloadGallery(gid, token) }, icon: <FileDownloadIcon /> },

            favorited ? { text: "取消收藏", onClick: () => { removeFavorite(gid, token) }, icon: <FavoriteBorderIcon /> }
                : { text: "收藏", onClick: () => { addFavorite(gid, token, getSetting("收藏夹", 9)) }, icon: <FavoriteIcon /> }
        ])
        setLongClickedName(name)
        setPos([x, y])
    }

    const handelNowDownloading = () => {
        setDownloadingPage(x => !x)
    }

    const action_goTop = {
        key :"action_goTop",
        name: "回到顶部",
        icon: <ArrowUpwardIcon />,
        onClick: () => { setRefreshToken(Math.random()) },
        closeOnClick: true,
    }
    const action_randomSort = {
        key:"action_randomSort",
        name: "随机排序",
        icon: <ShuffleIcon />,
        onClick: () => {
            setCardGidList((state) => randomSort(state));
            setRefreshToken(Math.random())
        },
        closeOnClick: true,


    }
    const action_nameHashSort = {
        key:"action_nameHashSort",
        name: "名称排序",
        icon: <SortByAlphaIcon />,
        onClick: () => {
            setCardGidList((state) => nameSort(state, cardInfoMap));
            setRefreshToken(Math.random())
        },
        closeOnClick: true,

    }
    const action_refresh = {
        key:"action_refresh",
        name: "刷新",
        icon: <CachedIcon />,
        onClick: () => {
            initClearAll()
            requestData()
        },
        closeOnClick: true,

    }
    const action_continueDownload = {
        key:"action_continueDownload",
        name: "",
        icon: <PlayArrowIcon />,
        onClick: () => { continueDownload() },
        closeOnClick: true,

    }

    const now_downloading = {
        key:"now_downloading",
        name: "",
        icon: downloadingPage ? <CheckCircleIcon /> : <DownloadingIcon />,
        onClick: () => { handelNowDownloading() },
        closeOnClick: false,
    }


    const request_next = {
        key:"request_next",
        name: `下一页`,
        icon: <KeyboardDoubleArrowRight />,
        onClick: () => { requestData() },
        closeOnClick: false,
    }

    const card_jump = {
        key:"card_jump",
        name: "跳转",
        icon: <LowPriorityIcon />,
        onClick: () => { handelJumpScrollOpen() },
        closeOnClick: false,
    }


    const normalActions = [request_next, card_jump, action_goTop, action_randomSort, action_nameHashSort, action_refresh]
    const downloadPageActions = [action_continueDownload, now_downloading, card_jump, action_goTop, action_randomSort, action_nameHashSort,]

    const historyRecord = useSettingBind("浏览历史", "100")

    const leftMenuItems = [
        {
            onClick: () => { props.openURL(leftMenuMap["自定义"], "") },
            icon: <TuneIcon />,
            text: "自定义"
        },
        {
            onClick: () => { props.openURL(leftMenuMap["主页"], "") },
            icon: <HomeIcon />,
            text: "主页"
        }, {
            onClick: () => { props.openURL(leftMenuMap["订阅"], "") },
            icon: <SubscriptionsIcon />,
            text: "订阅"
        }, {
            onClick: () => { props.openURL(leftMenuMap["热门"], "") },
            icon: <LocalFireDepartmentIcon />,
            text: "热门"
        }, {
            onClick: () => { props.openURL(leftMenuMap["收藏"], "") },
            icon: <FavoriteIcon />,
            text: "收藏"
        },
        {
            onClick: () => { props.openURL(leftMenuMap["下载"], "") },
            icon: <DownloadIcon />,
            text: "下载"
        },
        historyRecord !== "0" && {
            onClick: () => { props.openURL(leftMenuMap["历史"], "") },
            icon: <HistoryIcon />,
            text: "历史"
        },
        {
            onClick: () => { props.openURL(leftMenuMap["导入"], "") },
            icon: <FolderZipIcon />,
            text: "导入"
        },
        {
            onClick: () => { props.openURL(leftMenuMap["同步"], "") },
            icon: <SyncIcon />,
            text: "同步"
        },
        {
            onClick: () => { props.openURL(leftMenuMap["设置"], "") },
            icon: <SettingsIcon />,
            text: "设置"
        }
    ]


    const [searchFocus, setSearchFocus] = useState(false)
    const searchValue = useRef(props.initSearch)
    const setSearchValue = (value) => searchValue.current = value
    const doSearch = () => { if (searchValue.current !== "") { props.openURL("/search", `?f_search=${searchValue.current}`) } }

    return (
        <React.Fragment >
            <FloatSpeedDial
                actions={props.downloadPage ? downloadPageActions : normalActions}
                hidden={scrollControlledHidden}
                searchFocus={searchFocus}
                doSearch={doSearch}
            />
            <SecondConfirmDialog {...deleteSecondConfirm} />
            <JumpScroll
                open={jumpScrollOpen}
                handleClose={handelJumpScrollClose}
                targetID={containerUID.current}
                galleryCount={cardGidList.length}
            />
            <LongClickMenu
                pos={pos}
                setPos={setPos}
                items={longClickItems}
                title={longClickedName}
            />
            <LeftMenu
                open={leftMenuOpen}
                onClose={() => setLeftMenuOpen(false)}
                Items={leftMenuItems}
            />
            <TopSearchBar
                leftButtonClick={() => setLeftMenuOpen(true)}
                doSearch={doSearch}
                hidden={scrollControlledHidden}
                initText={props.initSearch}
                // setSearchValue={setSearchValue}
                onSearchValueChange={setSearchValue}
                searchFocus={searchFocus}
                onFocus={() => setSearchFocus(true)}
                onBlur={() => setSearchFocus(false)}
            />
            <VScrollCardContainer
                containerUID={containerUID.current}
                key={refreshToken}
                cardGidList={downloadingPage ? downloadingPageCardGidList : cardGidList}//gid list一定能在info map里找到
                cardInfoMap={cardInfoMap}//info map是先更新的
                setScrollTop={setScrollTop}
                loading={loading}
                onImageClick={props.openRead}
                onLongClick={handelLongClick}
                onCardClick={props.openGallery}
                onReachEnd={requestData}
            />
        </React.Fragment>
    )
}


const ItemsObserver = observer(MainPage_inner);

function MainPage(props) {
    return <div>
        <ItemsObserver {...props} />
    </div>
}

export default MainPage;
