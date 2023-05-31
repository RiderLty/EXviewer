
import ContentPasteIcon from '@mui/icons-material/ContentPaste';
import EditIcon from '@mui/icons-material/Edit';
import SendIcon from '@mui/icons-material/Send';
import ThumbDownAltIcon from '@mui/icons-material/ThumbDownAlt';
import ThumbDownOffAltIcon from '@mui/icons-material/ThumbDownOffAlt';
import ThumbUpAltIcon from '@mui/icons-material/ThumbUpAlt';
import ThumbUpOffAltIcon from '@mui/icons-material/ThumbUpOffAlt';
import { Backdrop, Button, ButtonBase, Grid, IconButton, InputBase, LinearProgress, Popover, } from '@mui/material';
import { styled } from '@mui/material/styles';
import { makeStyles } from '@mui/styles';
import { useLongPress } from 'ahooks';
import copy from 'clipboard-copy';
import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchComment, postComment, voteComment } from '../../api/serverApi';
import { notifyMessage } from '../../utils/PopoverNotifier';
import timeTools from '../../utils/TimeFormatTools';
import { useSmallMatches } from '../../utils/adaptiveBoxes';



const useStyles = makeStyles((theme) => ({
    head: {
        marginBottom: "10px",
        height: "15px",
        color: theme.palette.text.primary,
        textAlign: "justify",
        fontSize: "0.88rem",
        fontWeight: "bold",
        lineHeight: "1.6",
    },
    innerHTML: {
        color: theme.palette.text.primary,
        maxWidth: "100%",
        float: "left",
        textAlign: "left",
        fontSize: "0.85rem",
        lineHeight: "1.8",
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
    menuButton: {
        "&.MuiIconButton-colorInherit": {
            color: theme.palette.button.iconFunction.main,
            "&.Mui-disabled": {
                color: theme.palette.button.iconFunction.disabled,
            },
        },
    }

}));


const CommentPostEditor = ({ inputRef, onPost, editContent, editMode, editID }) => {
    const [text, setText] = useState(editContent);
    useEffect(() => {
        setText(editContent.slice(0, editContent.length - 1))
    }, [editContent])
    const [disabled, setDisabled] = useState(false);
    const post = async () => {
        if (text.length > 0) {
            setDisabled(true);
            const success = await onPost(text, editMode, editID);
            if (success) {
                setText("");
            }
            setDisabled(false);
        }
    }
    return <>
        <div style={{ width: "100%", height: 8 }} />
        <div
            style={{
                display: "flex",
                flexDirection: "row",
                alignItems: "flex-end",
                justifyContent: "flex-end",
            }}
        >
            <InputBase
                inputRef={inputRef}
                sx={{
                    width: "calc(100% - 52px)",
                    "& .MuiInputBase-input": {
                        color: "text.primary",
                        fontSize: "0.85rem",
                        lineHeight: "1.8",
                        "&.Mui-disabled": {
                            color: "text.disabled",
                            WebkitTextFillColor: "text.disabled",
                        }
                    }
                }}
                multiline
                variant="standard"
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={disabled}
                inputProps={{ "disableUnderline": true }}
            />
            <IconButton size="large" onClick={post} sx={{ float: "bottom" }} disabled={disabled}>
                {editMode ?
                    <EditIcon fontSize="inherit" sx={{ color: disabled ? "button.iconFunction.disabled" : "button.iconFunction.main" }} />
                    :
                    <SendIcon fontSize="inherit" sx={{ color: disabled ? "button.iconFunction.disabled" : "button.iconFunction.main" }} />
                }
            </IconButton>
        </div>
        <div style={{ backgroundColor: "#4C4C4C", width: "100%", height: "3px" }} />
    </>
}



const CommentClickMenu = ({ x, y, comment, canVote, onClose, onVote, onEdit }) => {//复制 点赞 点踩 删除自己的
    const classes = useStyles();
    const unFullScreen = useSmallMatches()
    const [fetching, setFetching] = useState(false);
    const [vote, setVote] = useState(comment.vote);
    useEffect(() => {
        setVote(comment?.vote || 0);
    }, [comment])

    const open = useMemo(() => {
        return x > -1 && y > -1
    }, [x, y])

    const copyComment = async (e) => {
        await copy(comment.text)
        notifyMessage("success", ["复制成功"])
    }

    const voteFunctionFactory = (value) => async (e) => {
        e.stopPropagation()
        setFetching(true)
        const [result, err] = await onVote(value)
        if (!err) {
            setFetching(false)
            setVote(result.vote)
            setTimeout(onClose, 300)
        } else {
            setFetching(false)
        }
    }
    const voteUp = voteFunctionFactory(1)
    const voteDown = voteFunctionFactory(-1)
    const editComment = async (e) => {
        e.stopPropagation()
        onClose()
        onEdit({
            editMode: true,
            editID: comment.commentID,
            editContent: comment.text
        })
    }

    return <Backdrop invisible={unFullScreen} open={open} onClick={onClose} sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }} >
        <Popover
            open={open}
            onClose={onClose}
            anchorReference="anchorPosition"
            anchorPosition={unFullScreen ? { left: x, top: y } : { left: document.body.clientWidth / 2, top: document.body.clientHeight / 2 }}
            transformOrigin={unFullScreen ? undefined : { vertical: 'center', horizontal: 'center', }}
            className={classes.menu}
        >
            <Grid
                container
                direction="row"
                justify="center"
                alignItems="center"
                sx={{ padding: "3px" }}
                spacing={"8px"}
            >
                <Grid item>
                    <IconButton color="inherit" className={classes.menuButton} size="large" onClick={copyComment}  >
                        <ContentPasteIcon fontSize="inherit" />
                    </IconButton>
                </Grid>
                {<Grid item>
                    <IconButton color="inherit" className={classes.menuButton} size="large" disabled={!canVote || fetching || comment?.isSelf || comment?.isUploader} onClick={voteUp}>
                        {vote === 1 ? <ThumbUpAltIcon fontSize="inherit" /> : <ThumbUpOffAltIcon fontSize="inherit" />}
                    </IconButton>
                </Grid>}
                {<Grid item>
                    <IconButton color="inherit" className={classes.menuButton} size="large" disabled={!canVote || fetching || comment?.isSelf || comment?.isUploader} onClick={voteDown}>
                        {vote === -1 ? <ThumbDownAltIcon fontSize="inherit" /> : <ThumbDownOffAltIcon fontSize="inherit" />}
                    </IconButton>
                </Grid>}
                {comment?.isSelf && <Grid item>
                    <IconButton color="inherit" className={classes.menuButton} size="large" onClick={editComment}>
                        <EditIcon fontSize="inherit" />
                    </IconButton>
                </Grid>}
            </Grid>
        </Popover >
    </Backdrop>
}

/**
 * 评论面板
 * width = 100%
 * height自动撑开
 * 外部控制两边留空
 * @param {Number} gid
 * @param {String} token
 * @param {Number} spacingPX
 * @param {object[]} comments
 */
export default function CommentPanel({ spacingPX, gid, token, comments }) {
    const BottomButton = styled(Button)(({ theme }) => ({
        marginTop: spacingPX + "px",
        color: theme.palette.button.loadMore.text,
        backgroundColor: theme.palette.button.loadMore.main,
        width: "100%",
        height: 50,
        "&:hover": {
            background: theme.palette.button.loadMore.hover,
        },
    }));
    const CommentContainer = styled(ButtonBase)(({ theme }) => ({
        padding: "8px 4px",
        borderRadius: 0,
        textTransform: "none",
        color: theme.palette.button.commentCard.text,
        backgroundColor: theme.palette.button.commentCard.main,
        "&:hover": {
            background: theme.palette.button.commentCard.hover,
        },
    }));

    const CommentRender = ({ row, index, onOpenMenu, commentSetter }) => {
        const ref = useRef(null);
        const onVote = async (vote) => {
            const [result, error] = await voteComment(gid, token, row.commentID, vote)
            if (!error) {
                commentSetter(old => old.map((c, i) => i === index ? { ...c, ...result } : c))
            }
            return [result, error]
        }
        const onClick = (e) => {
            if (e.target.nodeName === "A" && e.target.href) {
                //带地址的A标签
            } else if (e.target.parentNode.nodeName === "A" && e.target.parentNode.href) {
                //A标签包裹的带地址的图片
            } else {
                e.preventDefault();
                e.stopPropagation();
                onOpenMenu({
                    comment: row,
                    canVote: comments.canVote,
                    x: e.clientX,
                    y: e.clientY,
                    onVote: onVote,
                })
            }
        }
        useLongPress(onClick, ref, {//ipad上无法触发长按 ？
            delay: 300,
            preventDefault: true,
            stopPropagation: true,
        })

        return (<div style={{ width: "100%", }}>
            <CommentContainer
                style={{ width: "100%", }}
                ref={ref}
                onContextMenu={onClick}
                onClick={onClick}
            >
                <div style={{ width: "100%", }}>
                    <div className={classes.head}>
                        <div style={{ float: "left" }}><a style={{ marginRight: 16 }} >{"[" + timeTools.comment_time_reformat(row.post_date) + "]"}</a><a>{row.poster}{row.score === "" ? " (上传者)" : " "}</a></div>
                        <div style={{ float: "right" }}><a>{row.score}</a></div>
                    </div>
                    {
                        expanded ?
                            <div className={classes.innerHTML} dangerouslySetInnerHTML={{ __html: row.html }} /> :
                            <div className={classes.innerHTML}  >{row.short}</div>
                    }
                </div>
            </CommentContainer>
            <div style={{ backgroundColor: "#4C4C4C", width: "100%", height: "3px" }} />
        </div>)
    }


    const classes = useStyles();
    let comment_init_all_show = false//评论初始化是否全部显示
    const [commentData, setCommentData] = useState(comments.data);
    if (commentData.length <= 4) {
        let len_limit_reached = false;
        commentData.forEach((comment) => {
            len_limit_reached = len_limit_reached || comment.short.length > 40
        })
        comment_init_all_show = !len_limit_reached//评论小于4条 且每条长度小于40 则直接显示
    } else {
        comment_init_all_show = false//大于四条始终不全部显示
    }
    const [expanded, setExpanded] = useState(comment_init_all_show)

    const [canLoadMore, setCanLoadMore] = useState(!comments.all)
    const [loading, setLoading] = useState(false)
    const loadMoreComment = async () => {
        setCanLoadMore(false)
        setLoading(true)
        const [allComments, error] = await fetchComment(gid, token, true)
        if (error) {
            setCanLoadMore(true)
            notifyMessage("error", error)
        }
        else {
            setCommentData(allComments.data)
            setCanVote(allComments.canVote)
        }
        setLoading(false)
    }
    const [canVote, setCanVote] = useState(comments.canVote)
    const [commentClickMenuProps, setCommentClickMenuProps] = useState({
        comment: {},
        canVote: canVote,
        onVote: async () => { },
        x: -1,
        y: -1,
    })

    const commentPostInputRef = useRef(null)
    const [editProps, _setEditProps] = useState({ editMode: false, editID: -1, editContent: "" })
    const setEditProps = (editProps) => {
        _setEditProps(editProps)
        // console.log("commentPostInputRef", commentPostInputRef.current)
        // commentPostInputRef.current && commentPostInputRef.current.focus()
    }

    return (
        <div style={{ width: "100%", }}>
            <CommentClickMenu
                {...commentClickMenuProps}
                onClose={() => setCommentClickMenuProps(old => ({
                    ...old,
                    x: -1,
                    y: -1,
                }))}
                onEdit={setEditProps}
            />
            <Grid
                sx={{
                    width: "100%",
                }}
                container
                direction="column"
                justify="space-between"
                alignItems="left"
            >
                {
                    (expanded ? commentData : commentData.slice(0, 4)).map((row, index) => (
                        <CommentRender
                            key={row.commentID}
                            row={row}
                            index={index}
                            onOpenMenu={setCommentClickMenuProps}
                            commentSetter={setCommentData}
                        />
                    ))
                }
            </Grid>
            {
                expanded ?
                    <div >
                        <CommentPostEditor
                            inputRef={commentPostInputRef}
                            onPost={async (text, editMode, editID) => {
                                const [result, err] = await postComment(gid, token, text, editMode, editID)
                                if (err) {
                                    return false
                                } else {
                                    setCommentData(result.data)
                                    setCanVote(result.canVote)
                                    setCanLoadMore(!result.all)
                                    setEditProps({ editMode: false, editID: -1, editContent: "" })
                                }
                                return true //false
                            }}
                            {...editProps}
                        />
                        {
                            canLoadMore && <BottomButton
                                name='clickable'
                                onClick={loadMoreComment} >
                                {'加载更多'}
                            </BottomButton>
                        }
                        {loading && <LinearProgress sx={{ margin: "47px 0px" }} />}
                    </div>
                    :
                    <div >
                        <BottomButton
                            name='clickable'
                            onClick={() => { setExpanded(true) }} >
                            {'展开'}
                        </BottomButton>
                    </div>
            }
        </div>
    )

}