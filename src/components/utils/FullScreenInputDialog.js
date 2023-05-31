import CloseIcon from '@mui/icons-material/Close';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { Button, Grow, TextField } from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { useThrottleEffect, useThrottleFn } from 'ahooks';
import { useState } from 'react';
import CheckIcon from '@mui/icons-material/Check';


export default function FullScreenInputDialog({ open, handleClose, title, description, defaultText, verify, submit }) {
    //初始化时 内容为defaultText
    //不断verify 返回 true/false 验证并报错 内部节流
    //verify通过 则可以submit
    const [error, setError] = useState(false)
    const [text, setText] = useState(defaultText)
    useThrottleEffect( ()=>{setError(!verify(text))}, [text], { wait: 300, });
    return open ? <Dialog
        open={open}
        onClose={handleClose}
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
        <DialogTitle id="alert-dialog-title">
            {title}
        </DialogTitle>

        <DialogContent>
            <DialogContentText
                id="alert-dialog-description"
                sx={{ color: "text.primary", }}
            >
                {description}
            </DialogContentText>
            <TextField
                autoFocus
                fullWidth
                error={error}
                variant="outlined"
                margin="dense"
                label=""
                value={text}
                onChange={(e) => setText(e.target.value)}
            />
        </DialogContent>
        <DialogActions
            sx={{
                display: "flex",
                justifyContent: "space-between",
                // marginTop:0
            }}
        >
            <Button
                onClick={() => { submit(text) }}
                variant="text"
                disabled={error}
                startIcon={<CheckIcon />}
                sx={{
                    color: "#E91E63",
                }}
            >
                确认
            </Button>
            <Button
                onClick={handleClose}
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