import BrokenImageIcon from '@mui/icons-material/BrokenImage';
import { Box } from '@mui/material';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import React, { useEffect, useRef, useState } from 'react';
import Typography from '@mui/material/Typography';

function ImageLoader(props) {
    const [state, setState] = useState('loading')
    const refImg = useRef()
    const onLoad = () => {
        setState("finish")
    }
    const onError = () => {
        setState("error")
    }
    const reLoad = () => {
        if (refImg.current) {
            setState("loading")
            refImg.current.src = props.src
        }
    }

    return <>
        {state === 'loading' && <div style={{
            height: "auto",
            width: props.maxWidth,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
        }} >
            <Box sx={{ position: "relative", display: "inline-flex" }}>
                <CircularProgress />
                <Box
                    sx={{
                        top: 0,
                        left: 0,
                        bottom: 0,
                        right: 0,
                        position: "absolute",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center"
                    }}
                >
                    <Typography variant="caption" component="div" color="text.primary">
                        {props.index}
                    </Typography>
                </Box>
            </Box>
        </div>}
        {state === 'error' &&
            <div style={{
                height: "auto",
                width: props.maxWidth,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
            }} >
                <div style={{
                    width: "40%",
                    height: "40%",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                }}
                    onClick={reLoad}
                >
                    <BrokenImageIcon />
                </div></div>
        }

        {
            <img
                alt={props.src}
                ref={refImg}
                onLoad={onLoad}
                onError={onError}
                src={props.src}
                style={{
                    maxHeight: "100vh",
                    maxWidth: props.maxWidth,
                    display: state === "finish" ? "" : "none",
                }}
            />
        }
    </>
}

export default function MultiImageShow(props) {
    const mapSrc = []
    const maxWidth = props.urlInfos.length === 2 ? "50vw" : "100vw"
    if (props.urlInfos.length === 2) {
        if (props.lr) {
            mapSrc.push(props.urlInfos[1])
            mapSrc.push(props.urlInfos[0])
        } else {
            mapSrc.push(props.urlInfos[0])
            mapSrc.push(props.urlInfos[1])
        }
    } else {
        mapSrc.push(props.urlInfos[0])
    }
    return (
        <Grid
            sx={{
                width: "100vw",
                height: "100vh",
            }}
            container
            direction="row"
            justifyContent="center"
            alignItems="center"
        >
            {
                mapSrc.map((srcInfo, index) => {
                    return (
                        <ImageLoader
                            key={index}
                            src={srcInfo.url}
                            index={srcInfo.index}
                            maxWidth={maxWidth}
                        />
                    )
                })
            }
        </Grid>

    )
}
