//异步websocket接口

class AsyncWebsocketClass {
    constructor(url, options) {
        this.url = url;
        this.options = options;
        this.ws = null;
        this.msgQueue = [];
        this.recvQueue = [];
    }

    connect() {
        this.ws = new WebSocket(this.url, this.options);
        this.ws.onmessage = (msg) => {
            if (this.recvQueue.length > 0) {
                this.recvQueue.shift()(msg);
            } else {
                this.msgQueue.push(msg);
            }
        }
        return new Promise((resolve, reject) => {
            this.ws.onopen = () => {
                resolve(this.ws);
            }
        })
    }

    send(data) {
        return this.ws.send(data);
    }

    recv() {
        if (this.msgQueue.length > 0) {
            return new Promise((resolve, reject) => {
                resolve(this.msgQueue.shift());
            })
        } else {
            return new Promise((resolve, reject) => {
                this.recvQueue.push(resolve);
            })
        }
    }
    close() {
        this.ws.close();
    }
}

const getAsyncWebsocket = async (url, options) => {
    const ws = new AsyncWebsocketClass(url, options);
    await ws.connect();
    return ws;
}


export default getAsyncWebsocket;