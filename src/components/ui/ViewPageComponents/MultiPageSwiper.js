import React, { useEffect, useMemo, useState } from 'react';
import MultiImageShow from './MultiImageShow';
import TwoWaySwiper from './TwoWaySwiper';


const list2DoubleTuple = (list) =>
    list.reduce((acc, cur, index) => {
        index % 2 === 0 ? acc.push([cur]) : acc[acc.length - 1].push(cur)
        return acc
    }, [])

/**
 * 单页包含多张图片的swiper
 * @param {Object} props 
 * @param {Number} props.value
 * @param {function} props.setValue
 * @param {Boolean} props.reverse 
 * @param {Boolean} props.double
 * @param {Boolean} props.pagination
 * @param {string[]} props.urls
 */
export default function MultiPageSwiper(props) {
    const [value, _setValue] = useState(Number(props.value));

    const out2in = useMemo(() => {
        if (props.double) {
            if (props.pagination) {
                return Math.floor(props.value / 2) + 1//奇数对应
            } else {
                return Math.floor((props.value + 1) / 2)//偶数对应
            }
        } else {
            return props.value
        }
    }, [props.double, props.pagination, props.value])

    const in2out = (privateValue) => {
        if (props.double) {
            if (props.pagination) {
                return (privateValue - 1) * 2// + 1 //奇数对应
            } else {
                return privateValue * 2 //偶数对应
            }
        } else {
            return privateValue
        }
    }

    const setValue = (eventValue) => {
        _setValue(eventValue);
        props.setValue(in2out(eventValue));
    }

    useEffect(() => {
        out2in !== value && _setValue(out2in);
    }, [props.value])

    const getSplitUrls = () => {
        if (props.double) {
            if (props.pagination) {// [1,2] [3,4] [5,6] [7,8] ...
                return list2DoubleTuple(props.urls)
            } else {
                return [[props.urls[0]], ...list2DoubleTuple(props.urls.slice(1))]// [1] [2,3] [4,5]
            }
        } else {
            return props.urls.map(item => [item])//[1] [2] [3] [4] [5]
        }
    }
    const [splittedUrls, setSplittedUrls] = useState([])
    useEffect(() => { setSplittedUrls(getSplitUrls()) }, [props.urls, props.double, props.pagination])

    return (
        <TwoWaySwiper
            value={value}
            setValue={setValue}
            isReverse={props.reverse}
        >
            {
                splittedUrls.map((item, index) => {
                    return <MultiImageShow lr={props.reverse} key={index} urlInfos={item} />
                })
            }
        </TwoWaySwiper>

    )
}

