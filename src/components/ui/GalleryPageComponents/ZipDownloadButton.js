
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import IosShareIcon from '@mui/icons-material/IosShare';
import { CircularProgress, IconButton } from '@mui/material';
import FileSaver from 'file-saver';
import JsZip from 'jszip';
import jsPDF from "jspdf"
import React, { useState } from 'react';
import { fetchG_Data, getGalleryImgUrl } from '../../api/serverApi';
import { notifyMessage } from '../../utils/PopoverNotifier';
import { getSetting } from '../../utils/SettingHooks';

const fix8 = (num) => (Array(8).join(0) + num).slice(-8)

const spliceImage = async (imgList) => {
    const canvas = document.createElement('canvas');
    canvas.width = imgList[0].width
    let height = 0
    let heightList = []
    for (let img of imgList) {
        const scaleH = img.height * canvas.width / img.width
        height += scaleH
        heightList.push(height)
    }
    canvas.height = heightList[heightList.length - 1]
    const context = canvas.getContext('2d')
    for (let imgIndex in imgList) {
        const scaleH = imgList[imgIndex].height * canvas.width / imgList[imgIndex].width
        context.drawImage(imgList[imgIndex], 0, heightList[imgIndex] - scaleH, canvas.width, scaleH)
    }
    return canvas
}




const imgFetcher = async (urls, onLoad, onError, async) => {//异步 单线程 出错终止
    if (async) {
        let flag = true
        await Promise.all(urls.map( async (url, index) => {
            const resp = await fetch(url)
            if (resp.ok) {
                const blob = await resp.blob()
                await onLoad(index, blob)
            } else {
                onError(index)
                flag = false
            }
        }))
        return flag
    } else {
        for (let index = 0; index < urls.length; index++) {
            const resp = await fetch(urls[index])
            if (resp.ok) {
                const blob = await resp.blob()
                await onLoad(index, blob)
            } else {
                onError(index)
                return false
            }
        }
        return true
    }
}


/**
 * 下载ZIP
 * @param {object} props
 * @param {Number} props.gid
 * @param {String} props.token 
 * @returns 
 */
export default function ZipDownloadButton(props) {
    const [state, setState] = useState("init")
    const [initOpacity, setInitOpacity] = useState(1)
    const [processingOpacity, setProcessingOpacity] = useState(0)
    const [finishOpacity, setFinishOpacity] = useState(0)
    const [downloadProcess, setDownloadProcess] = useState(0)
    const [noError, setNoError] = useState(true)

    const initData = async () => {
        const [g_data, error] = await fetchG_Data(props.gid, props.token, true, false)
        if (error) {
            notifyMessage("error", ["Failed to fetch g_data.json"])
            setTimeout(() => { setNoError(false) }, 450);
            setTimeout(() => { setState("init") }, 500);
            setTimeout(() => { setInitOpacity(1) }, 600);
            return false
        } else {
            return {
                name: g_data.title_jpn || g_data.title,
                count: Number(g_data.filecount),
                g_data: g_data
            }
        }
    }

    const onSuccess = () => {
        setNoError(true)
        setTimeout(() => { setState("success") }, 500);
        setTimeout(() => { setFinishOpacity(1) }, 600);
        setTimeout(() => { setFinishOpacity(0) }, 1100);
        setTimeout(() => { setState("init") }, 1600);
        setTimeout(() => { setInitOpacity(1) }, 1700);
    }
    const onFailed = () => {
        setNoError(false)
        setTimeout(() => { setState("init") }, 500);
        setTimeout(() => { setInitOpacity(1) }, 600);
    }

    const makeZip = async () => {
        const args = await initData()
        if (args) {
            const zip = new JsZip();
            zip.file("g_data.json", JSON.stringify(args.g_data, null, 4))
            let over = 0
            const success = await imgFetcher(
                Array.from(Array(args.count), (v, k) => k + 1).map(i => getGalleryImgUrl(props.gid, props.token, i)),
                async (index, blob) => {
                    over++
                    setDownloadProcess(100 * over / args.count)
                    zip.file(`${fix8(index + 1)}.jpg`, blob)
                },
                (index) => notifyMessage("error", [`Failed to fetch ${fix8(index + 1)}.jpg`]),
                true
            )
            setProcessingOpacity(0)
            setInitOpacity(0)
            if (success) {
                zip.generateAsync({ type: "blob" }).then(function (content) {
                    FileSaver(content, args.name + ".zip");
                });
                onSuccess()
            } else {
                onFailed()
            }
        }
    }

    const makeImage = async () => {
        const args = await initData()

        if (args) {
            const bitMapList = []
            let over = 0
            const success = await imgFetcher(
                Array.from(Array(args.count), (v, k) => k + 1).map(i => getGalleryImgUrl(props.gid, props.token, i)),
                async (index, blob) => {
                    over++
                    setDownloadProcess(100 * over / args.count)
                    bitMapList.push(await createImageBitmap(blob))
                },
                (index) => notifyMessage("error", [`Failed to fetch ${fix8(index + 1)}.jpg`]),
                true
            )
            setProcessingOpacity(0)
            setInitOpacity(0)
            if (success) {
                onSuccess()
                const canvas = await spliceImage(bitMapList)
                try {
                    canvas.toBlob(
                        (blob) => {
                            if (blob) {
                                FileSaver(blob, args.name + ".jpg")
                            } else {
                                notifyMessage("error", ['尺寸过大', '请尝试导出其他格式'])
                            }
                        },
                        "image/jpeg",
                        0.5
                    )
                } catch (err) {
                    console.log("err", err)
                }
            } else {
                onFailed()
            }
        }
    }

    const makePDF = async () => {
        const args = await initData()
        let globalWidth = 1
        if (args) {
            let pdf = null
            let over = 0
            const success = await imgFetcher(
                Array.from(Array(args.count), (v, k) => k + 1).map(i => getGalleryImgUrl(props.gid, props.token, i)),
                async (index, blob) => {
                    over++
                    setDownloadProcess(100 * over / args.count)
                    const bitMap = await createImageBitmap(blob)
                    if (index === 0) {
                        globalWidth = bitMap.width
                        const scaleH = bitMap.height * globalWidth / bitMap.width
                        const orientation = scaleH > globalWidth ? "p" : "l"
                        pdf = new jsPDF(orientation, 'px', [globalWidth, scaleH])
                        pdf.addImage(URL.createObjectURL(blob), "JPEG", 0, 0, globalWidth, scaleH)
                    } else {
                        const scaleH = bitMap.height * globalWidth / bitMap.width
                        const orientation = scaleH > globalWidth ? "p" : "l"
                        pdf.addPage([globalWidth, scaleH], orientation)
                        pdf.addImage(URL.createObjectURL(blob), "JPEG", 0, 0, globalWidth, scaleH)
                    }
                },
                (index) => notifyMessage("error", [`Failed to fetch ${fix8(index + 1)}.jpg`]),
                false
            )
            setProcessingOpacity(0)
            setInitOpacity(0)
            if (success) {
                pdf.save(args.name)
                onSuccess()
            } else {
                onFailed()
            }
        }
    }

    const onClick = async () => {
        setInitOpacity(0)
        setProcessingOpacity(1)
        setTimeout(() => { setState("processing") }, 500)
        const exportType = getSetting("快捷导出格式", "zip")
        if (exportType === "zip") {//考虑改成单线程
            makeZip()
        } else if (exportType === "jpg") {
            makeImage()
        } else if (exportType === "pdf") {
            makePDF()
        } else {
            makeZip()
        }
    }
    const elemMap = {
        "init":
            <IconButton
                name='clickable'
                onClick={onClick}
                sx={{
                    opacity: initOpacity,
                    transition: ".5s",
                    color: "button.iconFunction.main",
                }}
                component="span"
            >
                {
                    noError ?
                        <IosShareIcon fontSize="large" />
                        :
                        <ErrorOutlineIcon fontSize="large" />

                }
            </IconButton>
        ,
        "processing":
            <div style={{ height: 50.99, width: 50.99, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <CircularProgress
                    // <CustomCircularProgress
                    size={"29.17px"}
                    thickness={4}
                    sx={{
                        opacity: processingOpacity,
                        transition: ".5s",
                        color: "button.iconFunction.process",
                    }}
                    variant="determinate"
                    value={downloadProcess}
                />
            </div>
        ,
        "success":
            <IconButton
                sx={{
                    opacity: finishOpacity,
                    transition: ".5s",
                    color: "button.iconFunction.main",
                }}
                aria-label="makeOver" component="span">
                <CheckCircleOutlineIcon fontSize="large" />
            </IconButton>
    }
    return elemMap[state]
}