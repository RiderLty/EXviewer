import { Slide } from "@mui/material";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useLocation } from "react-router";
import AppSetting from "../ui/AppSetting";
import GalleryPage from "../ui/GalleryPage";
import MainPage from "../ui/MainPage";
import UploadZip from "../ui/UploadZip";
import ViewPage from "../ui/ViewPage";
import { getSetting } from "./SettingHooks";
import SyncFromOther from "../ui/SyncFromOther";

const replaceLast = (arr, item) => arr.length === 0 ? [item] : [...arr.slice(0, -1), item]

/**
 *如果是受控制的路由跳转
 * 那么再location变化之前 history就已经完成更新
 * 表现为 history[-1] === location.pathname + location.search
 * 则pushElement
 * 非控制的路由跳转 例如返回 新打开网页
 * 如果history[-2] === location序列化 则是返回 直接pop
 * 否则就是新网页打开
 * pushElement
 * 重复的路由 外部不会触发location事件
 * 受控组件执行时候也应当屏蔽与history[-1]相同的跳转动作
 * @param {*} props 
 * @returns 
 */
export function SwitchRouter(props) {
    const location = useLocation()
    const navigate = useNavigate()
    const history = useRef([])//存放历史location序列化字符串
    const [elements, setElements] = useState([]);//history与elements一定是全映射的

    useEffect(() => {
        const pathname = decodeURIComponent(location.pathname)
        const search = decodeURIComponent(location.search)
        const locationTarget = `${pathname}${search}`
        const historyPeek = history.current[history.current.length - 1]

        if (historyPeek !== locationTarget) {//非受控 
            if (history.current.length > 1 && history.current[history.current.length - 2] === locationTarget) {
                history.current.pop()
                setElements(elements => elements.slice(0, -1))
            } else {
                history.current.push(locationTarget)
                const appendItem = pathRender(`${pathname}`, `${search}`)
                setElements(elements => [...elements, appendItem])
            }
        } else {
            //受控 添加到尾部
            const appendItem = pathRender(`${pathname}`, `${search}`)
            setElements(elements => [...elements, appendItem]);
        }
    }, [location])

    const openNew = (pathname, search) => {
        const target = `${pathname}${search}`
        if (history.current[history.current.length - 1] === target) {
            return
        } else {
            history.current.push(target)
            navigate(target)
            return
        }
    };//open new

    const openCurrent = (pathname, search) => {//
        const target = `${pathname}${search}`
        const top = history.current[history.current.length - 1]
        if (target !== top) {
            navigate(target, { replace: true })
            history.current = replaceLast(history.current, target)
            setElements(elements => elements.slice(0, -1));
        }
    };//把当前栈顶的location更新 组件也更新 浏览器地址不更新

    const replaceCurrentPathnames = new Set(['/', '/search', '/watched', '/popular', '/favorites', '/downloaded','/history', '/userFilter'])

    const openURL = (pathname, search) => {
        if (replaceCurrentPathnames.has(pathname)) {
            openCurrent(pathname, search)
        } else {
            openNew(pathname, search)
        }
    }

    const openRead = (gid, token) => openNew(`/viewing/${gid}/${token}`, '')

    const openGallery = (gid, token) => openNew(`/g/${gid}/${token}`, '')

    const openTagSearch = (row, tag) => {
        const tagText = `${row}:"${tag}$"`
        openNew("/search", `?f_search=${tagText}`)
    }

    const initSearch = (pathname, search) => {
        return decodeURIComponent(search).replace("&f_search=", "").replace("?f_search=", "")
    }

    const isDownloadPage = (pathname, search) => pathname === '/downloaded'

    const getApiURL = (pathname, search) => {
        const f_search_str = search.slice(0, 1) === "?" ? "&" + search.slice(1) : search
        //通过点击tag跳转 会改变真实路由 
        //通过搜索跳转不会
        //于是需要统一格式化为&搜索格式
        return {
            "/": "./list/?1=1",
            "/search": `./list/?1=1${f_search_str}`,
            "/watched": "./list/watched?1=1",
            "/popular": "./list/popular?1=1",
            "/favorites": "./list/favorites.php?1=1",
            "/downloaded": "",
            "/history":"./history/list",
            "/userFilter": "./list/?2=2",
        }[pathname]
    }


    const pathRender = (pathname, search) => {
        if ([
            "/",
            "/search",
            "/watched",
            "/popular",
            "/favorites",
            "/downloaded",
            "/history",
            "/userFilter"
        ].includes(pathname)) {
            return <MainPage
                key={`${pathname}_${search}`}
                pathname={pathname}
                search={search}
                initSearch={initSearch(pathname, search)}
                downloadPage={isDownloadPage(pathname, search)}
                apiURL={getApiURL(pathname, search)}
                openRead={openRead}
                openGallery={openGallery}
                openURL={openURL}
            />
        } else if (pathname.slice(0, 3) === "/g/") {
            return <GalleryPage
                key={pathname}
                gid={Number(pathname.split("/")[2])}
                token={pathname.split("/")[3]}
                openRead={openRead}
                onTagClick={openTagSearch}
            />
        } else if (pathname.slice(0, 9) === "/viewing/") {
            return <ViewPage
                key={pathname}
                gid={Number(pathname.split("/")[2])}
                token={pathname.split("/")[3]}
            />
        } else if (pathname.slice(0, 8) === "/setting") {
            return <AppSetting />
        } else if (pathname.slice(0, 10) === "/uploadZip") {
            return <UploadZip />
        } else if (pathname.slice(0, 14) === "/syncFromOther") {
            return <SyncFromOther />
        } else {
            return <a>UNKNOWN PATH</a>
        }
    }

    return (
        <div>
            {
                elements.map((elem, index) => (
                    <Slide key={index} in={true} appear={index !== 0} direction="left"  >
                        <div style={{ display: index === elements.length - 1 ? null : "none" }} >
                            {elem}
                        </div>
                    </Slide>
                ))
            }
        </div >
    )
}