import { useEffect, useRef, useState, useCallback } from 'react'

const FADE_IN_DURATION = 200
const FADE_OUT_DURATION = 800
const FADE_OUT_DELAY = 600
const THUMB_MIN_HEIGHT = 30
const THUMB_WIDTH = 4
const THUMB_BORDER_RADIUS = 2
const TRACK_MARGIN = 4

/**
 * 自定义滚动条指示器 — 仅指示位置，不可交互。
 * 滚动时渐入，停止后渐出。低存在感细条。
 *
 * @param {Object} props
 * @param {string} props.scrollContainerId - 可滚动容器的 DOM id
 * @param {number} [props.width=4] - 滚动条宽度(px)
 * @param {string} [props.color] - 滚动条颜色，默认跟随主题
 */
export default function CustomScrollbar({
    scrollContainerId,
    width = THUMB_WIDTH,
    color,
}) {
    const [visible, setVisible] = useState(false)
    const [opacity, setOpacity] = useState(0)
    const [thumbTop, setThumbTop] = useState(0)
    const [thumbHeight, setThumbHeight] = useState(0)
    const fadeOutTimerRef = useRef(null)
    const animFrameRef = useRef(null)
    const fadeStartRef = useRef(0)

    const updateThumb = useCallback(() => {
        const el = document.getElementById(scrollContainerId)
        if (!el) return
        const { scrollTop, scrollHeight, clientHeight } = el
        if (scrollHeight <= clientHeight) {
            setThumbHeight(0)
            return
        }
        const trackHeight = clientHeight - TRACK_MARGIN * 2
        const ratio = clientHeight / scrollHeight
        const h = Math.max(THUMB_MIN_HEIGHT, trackHeight * ratio)
        const maxTop = trackHeight - h
        const top = (scrollTop / (scrollHeight - clientHeight)) * maxTop + TRACK_MARGIN
        setThumbTop(top)
        setThumbHeight(h)
    }, [scrollContainerId])

    const fadeIn = useCallback(() => {
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
        if (fadeOutTimerRef.current) clearTimeout(fadeOutTimerRef.current)
        setVisible(true)
        setOpacity(1)
    }, [])

    const fadeOut = useCallback(() => {
        fadeStartRef.current = performance.now()
        const animate = (now) => {
            const elapsed = now - fadeStartRef.current
            const progress = Math.min(elapsed / FADE_OUT_DURATION, 1)
            setOpacity(1 - progress)
            if (progress < 1) {
                animFrameRef.current = requestAnimationFrame(animate)
            } else {
                setVisible(false)
                setOpacity(0)
            }
        }
        animFrameRef.current = requestAnimationFrame(animate)
    }, [])

    const handleScroll = useCallback(() => {
        updateThumb()
        fadeIn()
        if (fadeOutTimerRef.current) clearTimeout(fadeOutTimerRef.current)
        fadeOutTimerRef.current = setTimeout(fadeOut, FADE_OUT_DELAY)
    }, [updateThumb, fadeIn, fadeOut])

    useEffect(() => {
        const el = document.getElementById(scrollContainerId)
        if (!el) return
        el.addEventListener('scroll', handleScroll, { passive: true })
        // 初始计算
        updateThumb()
        return () => {
            el.removeEventListener('scroll', handleScroll)
            if (fadeOutTimerRef.current) clearTimeout(fadeOutTimerRef.current)
            if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
        }
    }, [scrollContainerId, handleScroll, updateThumb])

    // 监听容器尺寸变化
    useEffect(() => {
        const el = document.getElementById(scrollContainerId)
        if (!el) return
        const observer = new ResizeObserver(() => updateThumb())
        observer.observe(el)
        return () => observer.disconnect()
    }, [scrollContainerId, updateThumb])

    if (!visible || thumbHeight === 0) return null

    return (
        <div
            style={{
                position: 'fixed',
                top: 0,
                right: 0,
                width: width + TRACK_MARGIN,
                height: '100vh',
                pointerEvents: 'none',
                zIndex: 9999,
            }}
        >
            <div
                style={{
                    position: 'absolute',
                    top: thumbTop,
                    right: TRACK_MARGIN / 2,
                    width,
                    height: thumbHeight,
                    borderRadius: THUMB_BORDER_RADIUS,
                    backgroundColor: color || 'rgba(255, 255, 255, 0.3)',
                    opacity,
                    transition: `opacity ${FADE_IN_DURATION}ms ease-out`,
                }}
            />
        </div>
    )
}
