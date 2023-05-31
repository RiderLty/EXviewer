import { Button, Grid, TextField, Typography, Slider } from "@mui/material"
import { useState } from "react"
import { notifyMessage } from "../utils/PopoverNotifier";
import LinearProgress from '@mui/material/LinearProgress';
import Box from '@mui/material/Box';
import getAsyncWebsocket from "../utils/asyncWebsocket";
import { getWsUrl } from "../api/serverApi";
import { BorderContainer, ElemContainer } from "../utils/adaptiveBoxes";

function LinearProgressWithLabel(props) {
    return (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box sx={{ width: '100%', mr: 1 }}>
                <LinearProgress variant="determinate" {...props} />
            </Box>
            <Box sx={{ minWidth: 35 }}>
                {
                    Math.round(props.value,) === 100 ?
                        <Typography variant="body2" color="text.secondary">{`完成`}</Typography>
                        :
                        <Typography variant="body2" color="text.secondary">{`${Math.round(props.value,)}%`}</Typography>
                }
            </Box>
        </Box>
    );
}

export default function SyncFromOther({ }) {
    const [targetUrl, setTargetUrl] = useState("")
    const [wsInstance, setWsInstance] = useState(null)
    const [selectData, setSelectData] = useState(null)
    const [steep, setSteep] = useState(0)
    const [rangeValue, setRangeValue] = useState([0, 0]);

    const handleRangeValueChange = (event, newValue) => {
        setRangeValue(newValue);
    };

    const onSetUrl = async () => {
        setSelectData(null)
        wsInstance && wsInstance.close()
        const ws = await getAsyncWebsocket(getWsUrl("websocket/api/syncFromOtherServer"))
        setWsInstance(ws)
        ws.send(JSON.stringify({ url: targetUrl }))
        const [res, err] = JSON.parse((await ws.recv()).data)
        if (err) {
            notifyMessage("error", [err])
            setSteep(0)
            return
        }
        setSteep(1)
        setSelectData(res)
        setRangeValue([0, res.length])
    }



    const [process, setProcess] = useState(-1)
    const handelStartUpload = async () => {
        wsInstance.send(JSON.stringify(rangeValue))
        setSteep(2)
        while (true) {
            const [res, err] = JSON.parse((await wsInstance.recv()).data)
            if (err) {
                notifyMessage("error", [err])
                return
            }
            if (res === "finish") {
                break
            } else {
                setProcess(res)
            }
        }
        setSteep(3)
    }

    return <BorderContainer>
        {
            steep === 0 && <ElemContainer>
                <Grid
                    container
                    direction="row"
                    justifyContent="flex-start"
                    alignItems="flex-start"
                    spacing="6px"
                >
                    <Grid item xs={7}>
                        <TextField sx={{ width: "100%" }} placeholder="目标服务器地址" label="" variant="standard" value={targetUrl} onChange={(e) => setTargetUrl(e.target.value)} />
                    </Grid>
                    <Grid item xs={5}>
                        <Box display="flex" justifyContent="flex-end">
                            <Button variant="contained" onClick={onSetUrl} >
                                获取远程画廊
                            </Button>
                        </Box>
                    </Grid>
                </Grid>
            </ElemContainer>
        }
        {
            steep === 1 && <>
                <ElemContainer>
                    <Box sx={{ padding: "32px 24px 0px 24px" }}  >
                        <Slider
                            disabled={!selectData}
                            min={0}
                            max={selectData ? selectData.length : 0}
                            value={rangeValue}
                            onChange={handleRangeValueChange}
                            valueLabelDisplay="auto"
                        />
                    </Box>
                </ElemContainer>
                <ElemContainer>
                    <Button
                        variant="contained"
                        sx={{
                            width: "100%"
                        }}
                        onClick={handelStartUpload}
                    >开始同步</Button>
                </ElemContainer>
            </>
        }
        {
            steep === 2 && <ElemContainer>
                {
                    process === -1 ?
                        <Typography variant="body2" color="text.secondary">服务器正在获取画廊信息...</Typography> :
                        <LinearProgressWithLabel value={process} />
                }
            </ElemContainer>
        }
        {
            steep === 3 && <ElemContainer>
                <Typography variant="body2" color="text.secondary">已同步{rangeValue[1] - rangeValue[0]}个画廊</Typography>
            </ElemContainer>
        }
        <ElemContainer />
    </BorderContainer>
}