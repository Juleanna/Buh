import React from 'react'
import { Button, Dropdown } from 'antd'
import type { MenuProps } from 'antd'
import { FilePdfOutlined, FileExcelOutlined, DownOutlined } from '@ant-design/icons'
import { downloadFile, type ExportFormat } from '../utils/downloadPdf'

/* ------------------------------------------------------------------ */
/*  Full-size Dropdown.Button (for toolbars / card headers)           */
/* ------------------------------------------------------------------ */

interface ExportDropdownButtonProps {
  /** API url without format param, e.g. "/documents/asset/5/card/" */
  url: string
  /** Base filename without extension, e.g. "asset_card_5" */
  baseFilename: string
  /** Button label, default "Завантажити" */
  label?: string
  /** Custom icon for primary button */
  icon?: React.ReactNode
}

export const ExportDropdownButton: React.FC<ExportDropdownButtonProps> = ({
  url, baseFilename, label, icon,
}) => {
  const handle = (format: ExportFormat) => {
    const ext = format === 'xlsx' ? '.xlsx' : '.pdf'
    downloadFile(url, `${baseFilename}${ext}`, format)
  }

  const items: MenuProps['items'] = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: 'Завантажити PDF',
      onClick: () => handle('pdf'),
    },
    {
      key: 'xlsx',
      icon: <FileExcelOutlined />,
      label: 'Завантажити Excel',
      onClick: () => handle('xlsx'),
    },
  ]

  return (
    <Dropdown.Button
      menu={{ items }}
      onClick={() => handle('pdf')}
      icon={<DownOutlined />}
    >
      {icon || <FilePdfOutlined />}{' '}{label || 'Завантажити'}
    </Dropdown.Button>
  )
}

/* ------------------------------------------------------------------ */
/*  Compact icon-only dropdown (for table action columns)             */
/* ------------------------------------------------------------------ */

interface ExportIconButtonProps {
  url: string
  baseFilename: string
  /** Tooltip / title for the button */
  tooltip?: string
  /** Custom trigger icon, default FilePdfOutlined */
  icon?: React.ReactNode
}

export const ExportIconButton: React.FC<ExportIconButtonProps> = ({
  url, baseFilename, tooltip, icon,
}) => {
  const handle = (format: ExportFormat) => {
    const ext = format === 'xlsx' ? '.xlsx' : '.pdf'
    downloadFile(url, `${baseFilename}${ext}`, format)
  }

  const items: MenuProps['items'] = [
    {
      key: 'pdf',
      icon: <FilePdfOutlined />,
      label: 'PDF',
      onClick: () => handle('pdf'),
    },
    {
      key: 'xlsx',
      icon: <FileExcelOutlined />,
      label: 'Excel',
      onClick: () => handle('xlsx'),
    },
  ]

  return (
    <Dropdown menu={{ items }} trigger={['click']}>
      <Button size="small" icon={icon || <FilePdfOutlined />} title={tooltip} />
    </Dropdown>
  )
}
