
import CloseIcon from '@mui/icons-material/Close';
import { Button, Grow, TextField, Slider } from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import CheckIcon from '@mui/icons-material/Check';
import { useEffect, useMemo, useState } from 'react';
import { useThrottleEffect } from 'ahooks';
import { useCardDoubleRow, useSmallMatches } from './adaptiveBoxes';


export default function JumpScroll(props) {
    const break_matches = useCardDoubleRow();//是否双列展示
    const small_matches = useSmallMatches();//是否切换小尺寸card
    const getCurrentCardNum = () => document.getElementById(props.targetID) ? (break_matches ? 2 : 1) * Math.floor(document.getElementById(props.targetID).scrollTop / (small_matches ? 230 : 170)) : 0
    const calcTargetOffsetTop = (targetNum) => (small_matches ? 230 : 170) * targetNum / (break_matches ? 2 : 1)
    const verify = (text) => {
        try {
            return Number(text) >= 0 && Number(text) <= props.galleryCount
        } catch (error) {
            return false
        }
    }

    const [error, setError] = useState(false)

    const [pageCount, setPageCount] = useState(0)
    // const pageCountRev = useMemo(() => props.galleryCount - pageCount, [pageCount])

    useEffect(() => {
        setPageCount(props.galleryCount - getCurrentCardNum())
    }, [props.open])

    useThrottleEffect(() => { setError(!verify(pageCount)) }, [pageCount], { wait: 100, });

    return props.open ? <Dialog
        open={props.open}
        onClose={props.handleClose}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
        TransitionComponent={Grow}
        transitionDuration={300}
        sx={{
            "& .MuiDialog-paper": {
                color: "text.primary",
                backgroundColor: "page.background",
            }
        }}
    >

        <DialogContent
            style={{
                paddingBottom: 1
            }}

        >
            <DialogContentText
                id="alert-dialog-description"
                sx={{ color: "text.primary", }}
            >
                {`${props.galleryCount - getCurrentCardNum()} / ${props.galleryCount}`}
            </DialogContentText>
            <TextField
                autoFocus
                fullWidth
                error={error}
                variant="outlined"
                margin="dense"
                label=""
                value={pageCount}
                onChange={(e) => { setPageCount(e.target.value) }}
            />
            <Slider
                style={{ marginTop: 16 }}
                size="small"
                max={props.galleryCount}
                min={0}
                value={isNaN(pageCount) ? 0 :   props.galleryCount - pageCount }
            aria-label="Small"
            valueLabelDisplay="off"
            onChange={(e) => { setPageCount(props.galleryCount - e.target.value) }}
            />
        </DialogContent>
        <DialogActions
            sx={{
                display: "flex",
                justifyContent: "space-between",
            }}
        >
            <Button
                disabled={error}
                onClick={() => {
                    props.handleClose()
                    setTimeout(() => { document.getElementById(props.targetID).scrollTop = calcTargetOffsetTop(props.galleryCount - pageCount) }, 100)
                }}
                variant="text"
                startIcon={<CheckIcon />}
                sx={{
                    color: "#E91E63",
                }}
            >
                确认
            </Button>
            <Button
                onClick={props.handleClose}
                variant="text"
                startIcon={<CloseIcon />}
                sx={{
                    color: "text.primary",
                }}
            >
                取消
            </Button>
        </DialogActions>
    </Dialog> : null
}