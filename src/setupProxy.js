const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:7964',
      changeOrigin: true,
    })
  );
  app.use(
    '/websocket',
    createProxyMiddleware({
      target: 'ws://localhost:7964',
      changeOrigin: true,
      ws: true,
    })
  );
};