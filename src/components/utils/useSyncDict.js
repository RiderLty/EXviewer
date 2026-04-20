import { useEffect, useRef } from "react"

const SET_KV = 0
const DEL_K = 1
const LOAD = 3

const RECONNECT_DELAY = 3000

/**
 * 单SSE连接多频道复用。
 * handlers: { channelName: onEventCallback }
 * onEventCallback(eventType, ...args):
 *   - ('load', data)       全量加载
 *   - ('batch', sets, deletes)  批量增量更新
 */
export function useSSEHandler(sseUrl, handlers) {

    const versions = useRef({})       // { channel: version }
    const esRef = useRef(null)
    const reconnectTimerRef = useRef(null)
    const mountedRef = useRef(true)
    const pendingState = useRef({})   // { channel: { sets: {}, deletes: Set } }
    const flushTimerRef = useRef(null)

    const getPending = (channel) => {
        if (!pendingState.current[channel]) {
            pendingState.current[channel] = { sets: {}, deletes: new Set() }
        }
        return pendingState.current[channel]
    }

    const flush = () => {
        flushTimerRef.current = null
        const state = pendingState.current
        pendingState.current = {}
        for (const [channel, { sets, deletes }] of Object.entries(state)) {
            if (Object.keys(sets).length > 0 || deletes.size > 0) {
                handlers[channel]?.('batch', sets, [...deletes])
            }
        }
    }

    const scheduleFlush = () => {
        if (flushTimerRef.current === null) {
            flushTimerRef.current = setTimeout(flush, 0)
        }
    }

    const cancelFlush = () => {
        if (flushTimerRef.current !== null) {
            clearTimeout(flushTimerRef.current)
            flushTimerRef.current = null
        }
        pendingState.current = {}
    }

    useEffect(() => {
        mountedRef.current = true
        if (sseUrl === "") return

        const connect = () => {
            if (!mountedRef.current) return
            // 用已知频道版本构建查询参数
            const params = new URLSearchParams()
            const knownChannels = Object.keys(versions.current)
            if (knownChannels.length === 0) {
                // 首次连接，全量同步
            } else {
                for (const [channel, ver] of Object.entries(versions.current)) {
                    params.set(`${channel}_version`, ver)
                }
            }
            const url = params.toString()
                ? `${sseUrl}?${params.toString()}`
                : sseUrl
            const es = new EventSource(url)
            esRef.current = es

            es.onmessage = (event) => {
                try {
                    const recv = JSON.parse(event.data)
                    const channel = recv.channel
                    if (!channel || !handlers[channel]) return

                    if (recv.action === LOAD) {
                        delete pendingState.current[channel]
                        versions.current[channel] = recv.next
                        handlers[channel]('load', recv.data)
                    } else if (recv.action === SET_KV) {
                        if (recv.current === versions.current[channel]) {
                            versions.current[channel] = recv.next
                            const pending = getPending(channel)
                            pending.sets[recv.key] = recv.value
                            pending.deletes.delete(recv.key)
                            scheduleFlush()
                        }
                    } else if (recv.action === DEL_K) {
                        if (recv.current === versions.current[channel]) {
                            versions.current[channel] = recv.next
                            const pending = getPending(channel)
                            delete pending.sets[recv.key]
                            pending.deletes.add(recv.key)
                            scheduleFlush()
                        }
                    }
                } catch (e) {
                    console.error(e)
                }
            }

            es.onerror = () => {
                es.close()
                reconnect()
            }
        }

        const reconnect = () => {
            if (!mountedRef.current) return
            if (reconnectTimerRef.current) return
            reconnectTimerRef.current = setTimeout(() => {
                reconnectTimerRef.current = null
                connect()
            }, RECONNECT_DELAY)
        }

        connect()

        return () => {
            mountedRef.current = false
            clearTimeout(reconnectTimerRef.current)
            cancelFlush()
            if (esRef.current) {
                esRef.current.close()
            }
        }
    }, [])

    return null
}