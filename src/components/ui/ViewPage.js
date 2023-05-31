import { IconButton } from '@mui/material';
import React, { useEffect, useMemo, useState } from 'react';
import { Grid } from 'react-virtualized';
import { useRefState } from '../utils/MyHooks';
import { getSetting, useSettingBind } from '../utils/SettingHooks';
import MultiPageSwiper from './ViewPageComponents/MultiPageSwiper';
import RevSlider from './ViewPageComponents/RevSlider';
import ViewSettingPanel from './ViewPageComponents/ViewSettingPanel';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import VerticalScrollViewer from './ViewPageComponents/VerticalScrollViewer';
import { useEventListener } from 'ahooks';
import { addHistory, fetchG_Data, getGalleryImgUrl } from '../api/serverApi';

export default function ViewPage(props) {
    const [pageState, setPageState] = useState("init")
    const [errorInfo, setErrorInfo] = useState(["unknown error"])
    const [pages, setPages] = useState(0)
    const [title, setTitle] = useState("")

    const fetchData = async () => {
        const [g_data, error] = await fetchG_Data(props.gid, props.token, true, true)
        if (error) {
            setErrorInfo(error)
            setPageState("error")
        } else {
            setPages(Number(g_data.filecount))
            setTitle(g_data.title_jpn || g_data.title)
            setPageState("finish")
        }
    }
    useEffect(() => {
        fetchData()
        if (getSetting("浏览历史", "100") !== "0") {
            addHistory(props.gid, props.token)
        }
    }, [props.gid, props.token])

    return <div>
        {pageState === "init" ? <div /> : null}
        {pageState === "finish" ? <ViewPageUI
            {...props}
            pages={pages}
            title={title}
        /> : null}
        {pageState === "error" ? <Grid
            container
            direction="column"
            justifyContent="center"
            alignItems="center"
            sx={{
                height: "100%",
                width: "100%"
            }}
        >
            <IconButton
                sx={{
                    backgroundColor: "#00000000",
                    color: "primary.main",
                }}
                onClick={fetchData}
            >
                <AutorenewIcon sx={{ fontSize: 200 }} />
            </IconButton>
            <div
                style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'left',
                    margin: "100px 20px 0px 20px"
                }}
            >{
                    errorInfo.map(item => <a key={item}>{item}</a>)
                }</div>
        </Grid> : null}
    </div>

}


/**
 * 浏览界面
 * @param {object} props 
 * @param {Number} props.gid
 * @param {string} props.token
 * @param {Number} props.pages
 * @param {string} props.title
 */
function ViewPageUI(props) {
    document.title = props.title
    const gid = props.gid
    const token = props.token
    const pageCount = props.pages
    const urlInfos = Array(props.pages).fill().map((_, i) => ({
        url: getGalleryImgUrl(gid, token, i + 1),
        index: i + 1
    }))
    const [pageNumRef, pageNum, _setPageNum] = useRefState(Number(localStorage.getItem(`P_${gid}`)) || 1)
    const setPageNum = (value) => {
        if (pageNumRef.current === value) {
            return
        }
        const ensureMin = value < 1 ? 1 : value
        const ensureMax = ensureMin > pageCount ? pageCount : ensureMin
        _setPageNum(ensureMax);
        localStorage.setItem(`P_${gid}`, ensureMax);
        if (ensureMax === pageCount) {
            localStorage.removeItem(`P_${gid}`);
        }
    }

    const prevRange = 4
    const nextRange = useSettingBind("图片预加载", 7)
    const preload = () => {
        const start = pageNumRef.current - prevRange > 0 ? pageNumRef.current - prevRange : 1
        const end = pageNumRef.current + nextRange > pageCount ? pageCount : pageNumRef.current + nextRange
        for (let i = start; i <= end; i++) {
            let img = new Image();
            img.onload = () => {
                img = null
            }
            img.src = urlInfos[i - 1].url
        }
    }

    useEffect(() => {
        preload()
    }, [pageNum])


    const [sliderOpen, setSliderOpen] = useState(false)
    const onSliderClose = () => { setSliderOpen(false) }

    const [settingPanelOpen, setSettingPanelOpen] = useState(false)

    const handelTap = (event) => {
        const jmpNum = horizontalView ? 2 : 1
        const direction = switchDirection ? -1 : 1
        if (event.clientX / document.body.clientWidth > 0.7) {
            setPageNum(pageNum + direction * jmpNum)
        } else if (event.clientX / document.body.clientWidth < 0.3) {
            setPageNum(pageNum - direction * jmpNum)
        } else {
            if (event.clientY / document.body.clientHeight < 0.3) {
                setSettingPanelOpen(settingPanelOpen => !settingPanelOpen)
            }
            else if (event.clientY / document.body.clientHeight > 0.7) {
                setSliderOpen(sliderOpen => !sliderOpen)
            }
        }
    }

    const horizontalView = useSettingBind("横屏模式", false);
    const switchPagination = useSettingBind("分页模式", false);
    const switchDirection = useSettingBind("阅读方向", true);
    const readVertical = useSettingBind("竖屏阅读", false);

    const onViewSettingPanelClose = () => { setSettingPanelOpen(false) }
    const onViewSettingPanelOpen = () => { setSettingPanelOpen(true) }

    const refreshKey = useMemo(
        () => {
            return (horizontalView ? 4 : 0) + (switchPagination ? 2 : 0) + (switchDirection ? 1 : 0)
        }, [horizontalView, switchPagination, switchDirection]
    )


    const onKeyUP = (e) => {
        const jmpNum = getSetting("横屏模式") ? 2 : 1
        const direction = getSetting("阅读方向") ? -1 : 1
        if (e.code === "ArrowLeft") {
            setPageNum(pageNumRef.current - direction * jmpNum)
        } else if (e.code === "ArrowRight") {
            setPageNum(pageNumRef.current + direction * jmpNum)
        } else if (e.code === "Space" || e.code === "PageDown") {
            setPageNum(pageNumRef.current + jmpNum)
        } else if (e.code === "PageUp") {
            setPageNum(pageNumRef.current - jmpNum)
        }

    }
    useEventListener("keyup", onKeyUP)

    return (
        <div>
            <ViewSettingPanel
                open={settingPanelOpen}
                onClose={onViewSettingPanelClose}
                onOpen={onViewSettingPanelOpen}
            />
            <div style={{ height: '100vh', width: '100vw' }} onClick={handelTap}>
                {
                    readVertical ?
                        <VerticalScrollViewer
                            urlInfos={urlInfos}
                            value={pageNum}
                            setValue={setPageNum}
                        />
                        :
                        <MultiPageSwiper
                            key={refreshKey}//切换横屏模式  就重新渲染 避免了页数切换的BUG
                            value={pageNum}
                            setValue={setPageNum}
                            reverse={switchDirection}
                            double={horizontalView}
                            pagination={switchPagination}
                            urls={urlInfos}
                        />
                    // <CustomSwiper/>
                }
            </div>
            <RevSlider
                open={sliderOpen}
                onClose={onSliderClose}
                value={pageNum}
                setValue={setPageNum}
                reverse={switchDirection}
                max={pageCount}
            />
        </div>
    )
}

