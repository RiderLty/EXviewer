import React, { useEffect, useMemo, useRef, useState } from 'react';
import SwiperCore, { Controller, Keyboard, Mousewheel, Virtual } from 'swiper';
import { Swiper, SwiperSlide } from 'swiper/react';
// import 'swiper/swiper.scss';
import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';
import 'swiper/css/scrollbar';
// import "swiper/swiper-bundle.min.css";


SwiperCore.use([Virtual, Controller, Keyboard, Mousewheel]);

//反向滑动
//对外部表现正常而无语考虑内部顺序
//从1开始
//需要value  setValue children
export default function TwoWaySwiper({ isReverse, value, setValue, children }) {
    const out2in = () => isReverse ? children.length - value : value - 1
    const in2out = () => isReverse ? children.length - privateValueRef.current : privateValueRef.current + 1
    const [controller, setController] = useState(null)
    const controllerRef = useRef(null)
    const privateValueRef = useRef(out2in());
    const revChildren = useMemo(() => isReverse ? children.slice().reverse() : children, [isReverse, children])
    
    
    const setSwiperController = (swiperInstance) => {
        swiperInstance.slideTo(privateValueRef.current, 0)
        controllerRef.current = swiperInstance
        setController(swiperInstance)
    }

    const handelSlideChange = (e) => {
        privateValueRef.current = e.activeIndex;
        setValue(in2out());
    }

    useEffect(() => {
        if (controllerRef.current) {
            value < 1 && setValue(1)
            value > children.length && setValue(children.length)
            if (out2in() !== privateValueRef.current) {
                privateValueRef.current = out2in();
                controllerRef.current.slideTo(privateValueRef.current, 0)
            }
        }
    }, [value]);
    
    useEffect(() => {
        if (controllerRef.current != null) {
            privateValueRef.current = out2in();
            controllerRef.current.slideTo(privateValueRef.current, 0)
        }
    }, [children])
    
    return (
        children.length === 0 ?
            null :
            <Swiper
                spaceBetween={5}
                slidesPerView={1}
                virtual
                onSlideChange={handelSlideChange}
                onSwiper={setSwiperController}
                controller={{ control: controller }}
            >
                {
                    revChildren.map((item, index) => {
                        return (
                            <SwiperSlide key={index} >
                                {item}
                            </SwiperSlide>)
                    })
                }
            </Swiper>
    )
}