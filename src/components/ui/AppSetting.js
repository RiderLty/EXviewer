
import { Grid, Button, Switch, List, Menu, MenuItem } from "@mui/material";
import { makeStyles } from '@mui/styles';
import React, { useEffect, useState } from 'react';
import { clearHistory, fetchDiskCacheSize, requestClearDiskCache, requestDeleteOldGallery } from "../api/serverApi";
import { notifyMessage } from "../utils/PopoverNotifier";
import { useSetting } from "../utils/SettingHooks";
import FullScreenInputDialog from "../utils/FullScreenInputDialog";
import jsonpath from "jsonpath"
import { BorderContainer } from "../utils/adaptiveBoxes";


const useStyles = makeStyles((theme) => ({
    item: {
        height: "45px",
        "& a": {
            margin: "5px 10px 5px 10px",
        },

        "&.MuiMenuItem-root": {
            backgroundColor: theme.palette.background.main,
        },
        "&.MuiMenuItem-root.Mui-selected": {
            backgroundColor: theme.palette.background.main,
        },
        "&.MuiMenuItem-root.Mui-selected:hover": {
            backgroundColor: theme.palette.background.main,
        },
        "&.MuiMenuItem-root:hover": {
            backgroundColor: theme.palette.background.main,
        }
    },
    list: {
        "&.MuiList-root": {
            backgroundColor: theme.palette.background.main,
        },
    },
    menu: {
        "& .MuiList-root": {
            backgroundColor: theme.palette.background.main,
            padding: 0,
            borderRadius: 0,
        },
        "& .MuiPaper-root": {

            borderRadius: 5,
            backgroundColor: theme.palette.background.main,
        }
    },
    name_text: {
        color: theme.palette.text.primary,
        fontSize: "1rem",
    },
    help: {
        color: theme.palette.text.secondary,
        fontSize: "0.85rem",
        textTransform: "none",
        textAlign: "left",
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        display: '-webkit-box',
        WebkitLineClamp: '2',
        WebkitBoxOrient: 'vertical',

    },
    name_container: {
        minHeight: "35px",
        textAlign: "left",
        display: "grid",
    },



    splitLine: {
        width: "calc(100% - 40px)",
        height: "1px",
        marginLeft: "20px",
        marginRight: "20px",
        backgroundColor: theme.palette.text.secondary,
    }
}));



function SelectType(props) {
    const [value, setValue] = useSetting(props.name, props.defaultValue);
    const classes = useStyles();
    const [anchorEl, setAnchorEl] = useState(null);
    const open = Boolean(anchorEl);
    const handleClick = (e) => { setAnchorEl(e.currentTarget); };
    const handleClose = () => { setAnchorEl(null) };
    const onSelect = (value) => {
        setValue(value);
        handleClose()
    }
    return (
        <div>
            <Button
                onClick={handleClick}
                sx={{
                    height: "75px",
                    padding: "10px 20px 10px 20px",
                    borderRadius: "0px",
                    width: "100%",
                    color: "text.primary",
                    "&:hover": {
                        backgroundColor: "#00000000",
                    }
                }}
            >
                <Grid
                    container
                    direction="column"
                    justifyContent="space-between"
                    alignItems="flex-start"
                >
                    <Grid item>
                        <div className={classes.name_text}>
                            <a>{props.name}</a>
                        </div>
                    </Grid>
                    {
                        props.help ?
                            <Grid item>
                                <div className={classes.help}>
                                    <a>{props.help(value)}</a>
                                </div>
                            </Grid>
                            :
                            null
                    }
                </Grid>
            </Button>
            <Menu
                open={open}
                onClose={handleClose}
                className={classes.menu}
                anchorEl={anchorEl}
            >
                <List className={classes.list}  >
                    {
                        props.values.map((item, index) => <MenuItem
                            key={index}
                            className={classes.item}
                            onClick={() => onSelect(item)}
                        >
                            <a>{item}</a>
                        </MenuItem>)
                    }
                </List>
            </Menu>
        </div>
    )
}
function SwitchType(props) {
    const classes = useStyles();
    const [value, setValue] = useSetting(props.name, props.defaultValue);
    return (
        <Button
            sx={{
                height: "75px",
                padding: "10px 20px 10px 20px",
                borderRadius: "0px",
                width: "100%",
                color: "text.primary",
                "&:hover": {
                    backgroundColor: "#00000000",
                }
            }}
            onClick={() => setValue(!value)}
        >
            <Grid
                container
                direction="row"
                justifyContent="space-between"
                alignItems="center"
                sx={{
                    width: "100%",
                }}
            >
                <Grid item >
                    <Grid
                        container
                        direction="column"
                        justifyContent="space-between"
                        alignItems="flex-start"
                    >
                        <Grid item>
                            <div className={classes.name_text}>
                                <a>{props.name}</a>
                            </div>
                        </Grid>
                        {
                            props.help ?
                                <Grid item>
                                    <div className={classes.help}>
                                        <a>{props.help(value)}</a>
                                    </div>
                                </Grid>
                                :
                                null
                        }
                    </Grid>
                </Grid>
                <Grid item >
                    <Switch
                        edge="end"
                        checked={value}
                        inputProps={{
                            'aria-labelledby': 'switch-list-label-wifi',
                        }}
                    />
                </Grid>
            </Grid>
        </Button>
    )
}


function InputType(props) {
    const [value, setValue] = useSetting(props.name, props.defaultValue);
    const classes = useStyles();
    const [open, setOpen] = useState(false);
    const handleClick = () => { setOpen(true) };
    const handleClose = () => { setOpen(false) };
    const onSubmit = (text) => { handleClose(); setValue(text) }
    return (
        <div>
            <FullScreenInputDialog
                open={open}
                handleClose={handleClose}
                title={props.dialog.title}
                description={props.dialog.description}
                defaultText={value}
                verify={props.dialog.verify}
                submit={onSubmit}
            />
            <Button
                onClick={handleClick}
                sx={{
                    height: "75px",
                    padding: "10px 20px 10px 20px",
                    borderRadius: "0px",
                    width: "100%",
                    color: "text.primary",
                    "&:hover": {
                        backgroundColor: "#00000000",
                    }
                }}
            >
                <Grid
                    container
                    direction="column"
                    justifyContent="space-between"
                    alignItems="flex-start"
                >
                    <Grid item>
                        <div className={classes.name_text}>
                            <a>{props.name}</a>
                        </div>
                    </Grid>
                    {
                        props.help ?
                            <Grid item>
                                <div className={classes.help}>
                                    <a>{props.help(value)}</a>
                                </div>
                            </Grid>
                            :
                            null
                    }
                </Grid>
            </Button>
        </div>
    )
}


function FetchFunctionType({ name, help, initCallback, onClickCallback }) {
    //名称 帮助 
    //初始化回调函数 callback(setText)
    //点击回调函数 callback(setText)
    const classes = useStyles();
    const [text, setText] = useState('');

    useEffect(() => {
        initCallback(setText)
    }, [])

    return <Button
        sx={{
            height: "75px",
            padding: "10px 20px 10px 20px",
            borderRadius: "0px",
            width: "100%",
            color: "text.primary",
            "&:hover": {
                backgroundColor: "#00000000",
            }
        }}
        onClick={() => onClickCallback(setText)}
    >
        <Grid
            container
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{
                width: "100%",
            }}
        >
            <Grid item >
                <Grid
                    container
                    direction="column"
                    justifyContent="space-between"
                    alignItems="flex-start"
                >
                    <Grid item>
                        <div className={classes.name_text}>
                            <a>{name}</a>
                        </div>
                    </Grid>
                    {
                        help ?
                            <Grid item>
                                <div className={classes.help}>
                                    <a>{help}</a>
                                </div>
                            </Grid>
                            :
                            null
                    }
                </Grid>
            </Grid>
            <Grid item >
                <a>{text}</a>
            </Grid>
        </Grid>
    </Button>
}


const getDiskCacheSize = async (setText) => {
    const [data, error] = await fetchDiskCacheSize();
    if (error) {
        notifyMessage("error", error)
        setText("获取失败")
    } else {
        setText(data["msg"])
    }
}
const clearDiskCache = async (setText) => {
    setText("正在清除缓存...")
    const [data, error] = await requestClearDiskCache();
    if (error) {
        notifyMessage("error", error)
        setText("清除失败")
    } else {
        setText("已清除" + data["msg"])
    }
}

const clearViewHistory = async (setText) => {
    const [data, error] = await clearHistory();
    if (error) {
        notifyMessage("error", error)
        setText("清除失败")
    } else {
        setText("已清除" + data["msg"]+"条浏览记录")
    }
}

const deleteOldGallery = async (setText) => {
    setText("任务进行中...")
    const [data, error] = await requestDeleteOldGallery();
    if (error) {
        notifyMessage("error", error)
        setText("删除失败")
    } else {
        setText("已删除" + data["msg"] + "个画廊")
    }
}

export default function AppSetting(props) {
    const classes = useStyles();

    return (
        <BorderContainer>
            <Grid
                container
                direction="column"
                justifyContent="flex-start"
                alignItems="flex-start"
                sx={{
                    with: "100%",
                }}
            >
                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"启动页"}
                        defaultValue={"主页"}
                        values={["自定义", "主页", "订阅", "热门", "收藏", "下载"]}
                        help={(value) => `默认启动页 ${value}`}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }} >
                    <SwitchType
                        name={"下载时添加收藏"}
                        defaultValue={false}
                        help={(value) => value ? "下载画廊时添加到收藏夹" : "下载画廊时不添加到收藏夹"}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SwitchType
                        name={"删除时移除收藏"}
                        defaultValue={false}
                        help={(value) => value ? "删除下载的画廊时删除收藏" : "删除下载的画廊时不删除收藏"}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"色彩主题"}
                        defaultValue={"暗色"}
                        values={["跟随系统", "暗色", "亮色"]}
                        help={(value) => `${value}`}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"图片预加载"}
                        defaultValue={7}
                        values={[0, 3, 5, 7, 11, 13, 17]}
                        help={(value) => `向后预加载${value}张图片`}
                    />
                </Grid>
                <div className={classes.splitLine} />
                <Grid item xs={12} sx={{ width: "100%" }}>
                    <InputType
                        name={"双列显示宽度"}
                        defaultValue={"840"}
                        dialog={{
                            title: "",
                            description: "宽度大于此值时主页显示双列",
                            verify: (text) => !isNaN(parseFloat(text))
                        }}
                        help={(value) => value === "" ? "使用默认宽度" : `设定宽度为${value}`}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"收藏夹"}
                        defaultValue={9}
                        values={[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]}
                        help={(value) => `使用收藏夹${value}`}
                    />
                </Grid>


                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"浏览历史"}
                        defaultValue={"100"}
                        values={["0", "50", "100", "200","无限制"]}
                        help={(value) => {
                            if(value === 0 ) return "禁用浏览历史"
                            if(value === "无限制") return "不限制浏览历史数量"
                            return `保存${value}条浏览历史`
                        }}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <FetchFunctionType
                        name={"清除历史"}
                        help={"清除所有浏览历史"}
                        initCallback={(setText) => {}}
                        onClickCallback={clearViewHistory}
                    />
                </Grid>


                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SwitchType
                        name={"搜索本地画廊"}
                        defaultValue={false}
                        help={(value) => value ? "搜索结果优先显示已下载的画廊" : "不优先显示已下载的画廊"}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <InputType
                        name={"自定义筛选器"}
                        defaultValue={"*"}
                        dialog={{
                            title: "jsonpath",
                            description: "",
                            verify: (text) => {
                                try {
                                    jsonpath.query([], text)
                                    return true
                                } catch (err) {
                                    // console.log("jsonpath表达式错误", err)
                                    return false
                                }
                            }
                        }}
                        help={(value) => value === "*" ? "使用jsonpath筛选主页生成自定义列表" : value}
                    />
                </Grid>

                <div className={classes.splitLine} />
                <Grid item xs={12} sx={{ width: "100%" }}>
                    <InputType
                        name={"服务器URL"}
                        defaultValue={""}
                        dialog={{
                            title: "URL",
                            description: "例如 https://host.net/Exviewer/",
                            verify: (text) => {
                                if (text === "") return true
                                try {
                                    new URL("api/", text)
                                    return true
                                } catch (err) {
                                    return false
                                }
                            }
                        }}
                        help={(value) => value === "" ? "可指定其他API服务器URL，注意服务器需允许跨域" : new URL("api/", value).toString()}
                    />
                </Grid>
                <div className={classes.splitLine} />
                <Grid item xs={12} sx={{ width: "100%" }}>
                    <SelectType
                        name={"快捷导出格式"}
                        defaultValue={"zip"}
                        values={["zip", "jpg", "pdf"]}
                        help={(value) => `${value}`}
                    />
                </Grid>

                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <FetchFunctionType
                        name={"删除旧版本画廊"}
                        help={"更新数据库并删除旧版本画廊"}
                        initCallback={(setText) => { setText("") }}
                        onClickCallback={deleteOldGallery}
                    />
                </Grid>


                <div className={classes.splitLine} />

                <Grid item xs={12} sx={{ width: "100%" }}>
                    <FetchFunctionType
                        name={"清除缓存"}
                        help={"删除cache目录下所有文件"}
                        initCallback={getDiskCacheSize}
                        onClickCallback={clearDiskCache}
                    />
                </Grid>

            </Grid>
        </BorderContainer>
    )
}
