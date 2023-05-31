import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';
import { leftMenuMap } from './components/ui/MainPage';
import { getSetting } from './components/utils/SettingHooks';
import reportWebVitals from './reportWebVitals';

if(window.location.hash === ""){
  window.location.href = `${window.location.href}#${leftMenuMap[getSetting("启动页","主页")]}`
}

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
