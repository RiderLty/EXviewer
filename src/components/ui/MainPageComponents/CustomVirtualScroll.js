import LinearProgress from '@mui/material/LinearProgress';
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Collection } from 'react-virtualized';
import 'react-virtualized/styles.css';
import syncedDB, { DOWNLOAD_STATE, FAVORITE_STATE } from '../../utils/mobxSyncedState';
import GalleryCard from "./GalleryCard";
import { observer } from "mobx-react";
import { useEventListener } from 'ahooks';
import { Box } from '@mui/material';
import { useSmallMatches, useCardDoubleRow } from '../../utils/adaptiveBoxes'


// key={resizeKey}
// cellCount={props.cardGidList.length}
// cellRenderer={cellRenderer}
// cellSizeAndPositionGetter={cellSizeAndPositionGetter}
// onScroll={handelVScroll}
// height={(documentHeight || document.body.clientHeight)}
// width={(documentWidth || document.body.clientWidth) + 100}
// verticalOverscanSize={25}
// id={props.containerUID}

const styleMaker = (cellSizeAndPosition) => {
    // return {
    //     position: 'absolute',
    //     left: 0,
    //     top: 0,
    //     width: cellSizeAndPosition.width,
    //     height: cellSizeAndPosition.height,
    //     transform: `translate3d(${cellSizeAndPosition.x}px,${cellSizeAndPosition.y}px,0px)`,
    // }
    return {
        position: 'absolute',
        left: cellSizeAndPosition.x,
        top: cellSizeAndPosition.y,
        width: cellSizeAndPosition.width,
        height: cellSizeAndPosition.height,
    }
}
export default function CustomVirtualScroll({
    cellCount,
    cellRenderer,
    cellSizeAndPositionGetter,
    onScroll,
    height,
    width,
    verticalOverscanSize,
    id,
}) {
    const [displayOffsetLimit, setDisplayOffsetLimit] = useState([0, 25])
    const [containerHeight, setContainerHeight] = useState(0)
    useEffect(() => {
        if (cellCount && cellCount > 0) {
            const { height, width, x, y } = cellSizeAndPositionGetter({index:cellCount - 2})
            setContainerHeight(y + height + 263)
            // setContainerHeight(y + height + 183)
        }
    }, [cellCount, cellSizeAndPositionGetter])

    const calcDisplayOffsetLimit = () => {

    }
    const handelScroll = (e) => {
        onScroll(e.target)
    }
    useEffect(() => {
        calcDisplayOffsetLimit()
    }, [])
    return <div style={{ width: width + 100, height: height, overflow: "auto", position: "relative" }} id={id} onScroll={handelScroll}  >
        <div style={{ width: 100, height: containerHeight }} />
        {
            Array.from({ length: displayOffsetLimit[1] - displayOffsetLimit[0] }).map((_, index) =>
                cellRenderer({ key: index, index: index + displayOffsetLimit[0], isScrolling: false, style: styleMaker(cellSizeAndPositionGetter({ index: index + displayOffsetLimit[0] })) })
            )
        }
    </div>
}


