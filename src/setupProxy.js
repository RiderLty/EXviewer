const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND_HOST = process.env.REACT_APP_BACKEND_HOST || '192.168.3.3';
const BACKEND_PORT = process.env.REACT_APP_BACKEND_PORT || '7965';
const BACKEND_TARGET = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: BACKEND_TARGET,
      changeOrigin: true,
    })
  );
  // app.use(
  //   '/websocket',
  //   createProxyMiddleware({
  //     target: `ws://${BACKEND_HOST}:${BACKEND_PORT}`,
  //     changeOrigin: true,
  //     ws: true,
  //   })
  // );
};