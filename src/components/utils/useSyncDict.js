import { useEffect, useRef, useState } from "react"
import ReconnectingWebSocket from "reconnecting-websocket"

const INIT = 0
const READY = 1
const WAITING = 2

const SET_KV = 0
const DEL_K = 1
const SYNC_ALL = 2
const LOAD = 3

export function useWsHandeler(wsUrl, onEvent) {

    const version = useRef(-1)
    const state = useRef(INIT)
    const ws = useRef(null)
    const pendingSets = useRef({})
    const pendingDeletes = useRef(new Set())
    const flushTimerRef = useRef(null)

    const flush = () => {
        flushTimerRef.current = null
        const sets = pendingSets.current
        const deletes = [...pendingDeletes.current]
        pendingSets.current = {}
        pendingDeletes.current = new Set()
        if (Object.keys(sets).length > 0 || deletes.length > 0) {
            onEvent('batch', sets, deletes)
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
        pendingSets.current = {}
        pendingDeletes.current = new Set()
    }

    useEffect(() => {
        if (ws.current) return;
        const onmessage = (event) => {
            const recv = JSON.parse(event.data);
            try {
                if (state.current === READY) {
                    if (recv.current === version.current) {
                        version.current = recv.next;
                        if (recv.action === SET_KV) {//set
                            pendingSets.current[recv.key] = recv.value
                            pendingDeletes.current.delete(recv.key)
                            scheduleFlush()
                        } else if (recv.action === DEL_K) {//delete
                            delete pendingSets.current[recv.key]
                            pendingDeletes.current.add(recv.key)
                            scheduleFlush()
                        } else if (recv.action === LOAD) {
                            cancelFlush()
                            onEvent('load', recv.data)
                        }
                    } else {
                        cancelFlush()
                        state.current = WAITING;
                        ws.current.send("sync")
                    }
                } else {
                    if (recv.action === SYNC_ALL) {//sync all
                        version.current = recv.next
                        cancelFlush()
                        onEvent('load', recv.data)
                        state.current = READY;
                    }
                }
            } catch (e) {
                console.error(e)
            }
        }
        const onopen = () => {
            console.log("ws open!")
            ws.current.send("sync")
        }
        if (wsUrl !== "") {
            ws.current = new ReconnectingWebSocket(wsUrl, [], {
                maxReconnectionDelay: 100,
            })
            ws.current.addEventListener("message", onmessage)
            ws.current.addEventListener("open", onopen)
        }
        return () => {
            cancelFlush()
            if (ws.current && ws.current.readyState === 1) {
                ws.current.close()
            }
        }
    })
    return null
}


const delKeyFromObj = (dict, key) => {
    const newDict = { ...dict }
    delete newDict[key]
    return newDict
}

const deleteKey = (key) => {
    return (dict) => {
        return delKeyFromObj(dict, key)
    }
}

const combineDict = (newDict) => {
    return (oldDict) => {
        return { ...oldDict, ...newDict }
    }
}


export default function useSyncDict(wsUrl) {
    const [data, setData] = useState({
        keySet: new Set(),
        dict: {}
    })
    const version = useRef(-1)
    const state = useRef(INIT)
    const ws = useRef(null)
    const pendingSets = useRef({})
    const pendingDeletes = useRef(new Set())
    const flushTimerRef = useRef(null)

    const flush = () => {
        flushTimerRef.current = null
        const sets = pendingSets.current
        const deletes = [...pendingDeletes.current]
        pendingSets.current = {}
        pendingDeletes.current = new Set()
        if (Object.keys(sets).length > 0 || deletes.length > 0) {
            setData(old => {
                let newDict = { ...old.dict, ...sets }
                for (const key of deletes) {
                    delete newDict[key]
                }
                return { keySet: new Set(Object.keys(newDict)), dict: newDict }
            })
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
        pendingSets.current = {}
        pendingDeletes.current = new Set()
    }

    useEffect(() => {
        if (ws.current) return;
        const onmessage = (event) => {
            const recv = JSON.parse(event.data);
            try {
                if (state.current === READY) {
                    if (recv.current === version.current) {
                        version.current = recv.next;
                        if (recv.action === SET_KV) {//set
                            pendingSets.current[recv.key] = recv.value
                            pendingDeletes.current.delete(recv.key)
                            scheduleFlush()
                        } else if (recv.action === DEL_K) {//delete
                            delete pendingSets.current[recv.key]
                            pendingDeletes.current.add(recv.key)
                            scheduleFlush()
                        } else if (recv.action === LOAD) {
                            cancelFlush()
                            setData(recv.data)
                        }
                    } else {
                        cancelFlush()
                        state.current = WAITING;
                        ws.current.send("sync")
                    }
                } else {
                    if (recv.action === SYNC_ALL) {//sync all
                        version.current = recv.next
                        cancelFlush()
                        setData(recv.data)
                        state.current = READY;
                    }
                }
            } catch (e) {
                console.error(e)
            }
        }
        const onopen = () => {
            ws.current.send("sync")
        }
        ws.current = new ReconnectingWebSocket(wsUrl, [], {
            maxReconnectionDelay: 100,
        })
        ws.current.addEventListener("message", onmessage)
        ws.current.addEventListener("open", onopen)
        return () => {
            cancelFlush()
            if (ws.current && ws.current.readyState === 1) {
                ws.current.close()
            }
        }
    })
    return data
}