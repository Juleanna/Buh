import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, App as AntdApp } from 'antd'
import ukUA from 'antd/locale/uk_UA'
import dayjs from 'dayjs'
import 'dayjs/locale/uk'
import App from './App'
import './resizable.css'
import { AntdStaticProvider } from './utils/globalMessage'

dayjs.locale('uk')

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={ukUA}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <AntdApp>
        <AntdStaticProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <App />
          </BrowserRouter>
        </AntdStaticProvider>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
