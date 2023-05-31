import CloseIcon from '@mui/icons-material/Close';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import ScreenRotationIcon from '@mui/icons-material/ScreenRotation';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import Grow from '@mui/material/Grow';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import { styled } from '@mui/material/styles';
import Switch from '@mui/material/Switch';
import PropTypes from 'prop-types';
import React from 'react';
import { useSetting } from '../../utils/SettingHooks';
import SwipeVerticalIcon from '@mui/icons-material/SwipeVertical';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const Transition = React.forwardRef(function Transition(props, ref) {
    return <Grow direction="up" ref={ref} {...props} />;
});

const BootstrapDialog = styled(Dialog)(({ theme }) => ({
    '& .MuiDialogContent-root': {
        padding: theme.spacing(2),
    },
    '& .MuiDialogActions-root': {
        padding: theme.spacing(1),
    },
}));

const BootstrapDialogTitle = (props) => {
    const { children, onClose, ...other } = props;

    return (
        <DialogTitle sx={{ m: 0, p: 2, backgroundColor: "page.background" }} {...other}>
            {children}
            {onClose ? (
                <IconButton
                    aria-label="close"
                    onClick={onClose}
                    sx={{
                        position: 'absolute',
                        right: 8,
                        top: 8,
                        color: (theme) => theme.palette.primary.main,
                    }}
                >
                    <CloseIcon />
                </IconButton>
            ) : null}
        </DialogTitle>
    );
};

BootstrapDialogTitle.propTypes = {
    children: PropTypes.node,
    onClose: PropTypes.func.isRequired,
};


/**
 * 阅读设置面板
 * @param {object} props 
 * @param {Boolean} props.open
 * @param {Boolean} props.onOpen
 * @param {Boolean} props.onClose
 */


export default function ViewSettingPanel(props) {
    const [horizontalView, setHorizontalView] = useSetting("横屏模式", false);
    const [switchPagination, setSwitchPagination] = useSetting("分页模式", false);
    const [switchDirection, setSwitchDirection] = useSetting("阅读方向", true);
    const [readVertical, setReadVertical] = useSetting("竖屏阅读", false);
    return (
        <div>
            <BootstrapDialog
                TransitionComponent={Transition}
                onClose={props.onClose}
                aria-labelledby="customized-dialog-title"
                open={props.open}
                sx={{
                    "& .MuiDialog-paper": {
                        backgroundColor: "page.background",
                    },
                }}
            >
                <BootstrapDialogTitle id="customized-dialog-title" onClose={props.onClose}>
                    阅读设置
                </BootstrapDialogTitle>
                <List
                    sx={{
                        width: '100%',
                        maxWidth: 360,
                        backgroundColor: 'page.background',
                        color: "text.primary",
                    }}
                >
                    <ListItem>
                        <ListItemIcon>
                            <SwipeVerticalIcon color='primary' />
                        </ListItemIcon>
                        <ListItemText primary="竖向滚动" />
                        <Switch
                            edge="end"
                            onChange={() => {
                                if(readVertical === false){
                                    setHorizontalView(false)
                                }
                                setReadVertical(!readVertical)
                            }}
                            checked={readVertical}
                        />
                    </ListItem>
                    {
                        !readVertical ? <div>
                            <ListItem>
                                <ListItemIcon>
                                    <ScreenRotationIcon color='primary' />
                                </ListItemIcon>
                                <ListItemText primary="双页阅读" />
                                <Switch
                                    edge="end"
                                    onChange={() => setHorizontalView(!horizontalView)}
                                    checked={horizontalView}
                                />
                            </ListItem>
                            {horizontalView ? <ListItem>
                                <ListItemIcon>
                                    <ViewColumnIcon color='primary' />
                                </ListItemIcon>
                                <ListItemText primary="切换分页" />
                                <Switch
                                    edge="end"
                                    onChange={() => setSwitchPagination(!switchPagination)}
                                    checked={switchPagination}
                                />
                            </ListItem> : null}
                        </div> : null
                    }
                    <ListItem  >
                        <ListItemIcon>
                            <MenuBookIcon color='primary' />
                        </ListItemIcon>
                        <ListItemText primary="阅读方向" />
                        <IconButton  onClick={() => setSwitchDirection(!switchDirection)}  >
                            <ArrowBackIcon color='primary'  sx={{
                                transition: ".3s",
                                transform:   switchDirection ?  "" :"rotateZ(180deg)"
                            }} />
                        </IconButton>
                    </ListItem>
                    <ListItem>
                        <Button sx={{ width: "100%" }} variant="contained" startIcon={<RestartAltIcon />}
                            onClick={() => {
                                setHorizontalView(false);
                                setSwitchPagination(false);
                                setSwitchDirection(true);
                                props.onClose();
                            }}
                        >
                            重置设置
                        </Button>
                    </ListItem>
                </List>
            </BootstrapDialog>
        </div>
    );
}
