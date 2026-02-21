import React from 'react'
import { App } from 'antd'
import type { MessageInstance } from 'antd/es/message/interface'
import type { ModalStaticFunctions } from 'antd/es/modal/confirm'

let _message: MessageInstance
let _modal: Omit<ModalStaticFunctions, 'warn'>

export const message: MessageInstance = new Proxy({} as MessageInstance, {
  get(_target, prop) {
    return _message?.[prop as keyof MessageInstance]
  },
})

export const modal = new Proxy({} as Omit<ModalStaticFunctions, 'warn'>, {
  get(_target, prop) {
    return _modal?.[prop as keyof Omit<ModalStaticFunctions, 'warn'>]
  },
})

/**
 * Render this component inside <App> to capture the context-aware message & modal API.
 */
export const AntdStaticProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const app = App.useApp()
  _message = app.message
  _modal = app.modal
  return <>{children}</>
}
