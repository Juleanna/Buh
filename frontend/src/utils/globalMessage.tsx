import React from 'react'
import { App } from 'antd'
import type { MessageInstance } from 'antd/es/message/interface'

let _message: MessageInstance

export const message: MessageInstance = new Proxy({} as MessageInstance, {
  get(_target, prop) {
    return _message?.[prop as keyof MessageInstance]
  },
})

/**
 * Render this component inside <App> to capture the context-aware message API.
 */
export const AntdStaticProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const app = App.useApp()
  _message = app.message
  return <>{children}</>
}
