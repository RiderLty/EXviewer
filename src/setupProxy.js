const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://192.168.3.3:7964',
      changeOrigin: true,
    })
  );
  app.use(
    '/websocket',
    createProxyMiddleware({
      target: 'ws://192.168.3.3:7964',
      changeOrigin: true,
      ws: true,
    })
  );
};