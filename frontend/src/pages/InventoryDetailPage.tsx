import React, { useEffect, useState, useRef, useCallback } from 'react'
import {
  Table, Typography, Card, Descriptions, Tag, Button, Space, Switch,
  InputNumber, Select, Spin, Modal, Input, Row, Col, Alert,
  Badge, Statistic,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  ArrowLeftOutlined, ScanOutlined,
  CheckCircleOutlined, CloseCircleOutlined, PrinterOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportDropdownButton } from '../components/ExportButton'
import type { Inventory, InventoryItem } from '../types'

const { Title, Text } = Typography

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
}

const CONDITION_OPTIONS = [
  { value: 'good', label: 'Справний' },
  { value: 'needs_repair', label: 'Потребує ремонту' },
  { value: 'unusable', label: 'Непридатний' },
]

const InventoryDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [inventory, setInventory] = useState<Inventory | null>(null)
  const [items, setItems] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)

  // QR Scanner state
  const [scannerOpen, setScannerOpen] = useState(false)
  const [scanStatus, setScanStatus] = useState<'idle' | 'found' | 'already' | 'not_found'>('idle')
  const [scanAssetName, setScanAssetName] = useState('')
  const scannerRef = useRef<any>(null)
  const videoRef = useRef<HTMLDivElement>(null)

  const loadData = useCallback(async () => {
    const [invRes, itemsRes] = await Promise.all([
      api.get(`/assets/inventories/${id}/`),
      api.get('/assets/inventory-items/', { params: { inventory: id } }),
    ])
    setInventory(invRes.data)
    setItems(itemsRes.data.results || itemsRes.data)
    setLoading(false)
  }, [id])

  useEffect(() => { loadData() }, [loadData])

  const updateItem = async (itemId: number, field: string, value: unknown) => {
    try {
      await api.patch(`/assets/inventory-items/${itemId}/`, { [field]: value })
      loadData()
    } catch {
      message.error('Помилка збереження')
    }
  }

  // Parse QR code text to extract inventory number
  const parseQrText = (text: string): string => {
    const match = text.match(/Інв\.номер:\s*(.+?)(?:\n|$)/)
    if (match) return match[1].trim()
    return text.trim()
  }

  // Handle QR scan result — find and mark item
  const handleScanResult = useCallback(async (invNumber: string) => {
    const foundItem = items.find(i => i.asset_inventory_number === invNumber)

    if (foundItem) {
      if (!foundItem.is_found) {
        setScanStatus('found')
        setScanAssetName(`${foundItem.asset_inventory_number} — ${foundItem.asset_name}`)
        try {
          await api.patch(`/assets/inventory-items/${foundItem.id}/`, { is_found: true })
          message.success(`Знайдено: ${foundItem.asset_name}`)
          loadData()
        } catch {
          message.error('Помилка оновлення')
        }
      } else {
        setScanStatus('already')
        setScanAssetName(`${foundItem.asset_inventory_number} — ${foundItem.asset_name}`)
        message.info(`Вже зареєстровано: ${foundItem.asset_name}`)
      }
    } else {
      setScanStatus('not_found')
      setScanAssetName(invNumber)
      message.warning(`ОЗ "${invNumber}" не знайдено в цій інвентаризації`)
    }

    setTimeout(() => {
      setScanStatus('idle')
      setScanAssetName('')
    }, 3000)
  }, [items, loadData])

  // Start QR scanner
  const startScanner = async () => {
    setScannerOpen(true)
    setScanStatus('idle')

    const { Html5Qrcode } = await import('html5-qrcode')

    setTimeout(async () => {
      try {
        const scanner = new Html5Qrcode('qr-reader')
        scannerRef.current = scanner

        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 250, height: 250 } },
          (decodedText) => {
            const invNumber = parseQrText(decodedText)
            handleScanResult(invNumber)
          },
          () => {}
        )
      } catch {
        message.error('Не вдалося отримати доступ до камери')
        setScannerOpen(false)
      }
    }, 300)
  }

  const stopScanner = async () => {
    if (scannerRef.current) {
      try {
        await scannerRef.current.stop()
        scannerRef.current.clear()
      } catch { /* ignore */ }
      scannerRef.current = null
    }
    setScannerOpen(false)
  }

  const handleManualInput = (value: string) => {
    if (value.trim()) handleScanResult(value.trim())
  }

  const handlePrintQR = async () => {
    const assetIds = items.map(i => i.asset)
    if (!assetIds.length) { message.warning('Немає позицій'); return }
    try {
      const response = await api.post('/assets/qr/bulk/', { asset_ids: assetIds }, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/zip' })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = `qr_inventory_${inventory?.number || id}.zip`
      link.click()
      URL.revokeObjectURL(link.href)
      message.success('QR-коди завантажено')
    } catch {
      message.error('Помилка завантаження QR-кодів')
    }
  }

  if (loading || !inventory) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const isEditable = inventory.status !== 'completed'
  const foundCount = items.filter(i => i.is_found).length
  const shortages = items.filter(i => !i.is_found).length
  const totalItems = items.length

  const columns = [
    { title: 'Інв. номер', dataIndex: 'asset_inventory_number', key: 'inv', width: 120 },
    { title: 'Назва ОЗ', dataIndex: 'asset_name', key: 'name', ellipsis: true },
    {
      title: 'Облікова вартість', dataIndex: 'book_value', key: 'book', width: 150,
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
      responsive: ['md' as const],
    },
    {
      title: 'Наявність', dataIndex: 'is_found', key: 'found', width: 100,
      render: (val: boolean, record: InventoryItem) => isEditable ? (
        <Switch checked={val} onChange={(v) => updateItem(record.id, 'is_found', v)} />
      ) : (
        <Tag color={val ? 'green' : 'red'}>{val ? 'Так' : 'Ні'}</Tag>
      ),
    },
    {
      title: 'Стан', dataIndex: 'condition', key: 'condition', width: 170,
      responsive: ['lg' as const],
      render: (val: string, record: InventoryItem) => isEditable ? (
        <Select value={val} onChange={(v) => updateItem(record.id, 'condition', v)}
          options={CONDITION_OPTIONS} style={{ width: 155 }} size="small" />
      ) : record.condition_display,
    },
    {
      title: 'Факт. вартість', dataIndex: 'actual_value', key: 'actual', width: 150,
      responsive: ['lg' as const],
      render: (val: string | null, record: InventoryItem) => isEditable ? (
        <InputNumber value={val ? Number(val) : undefined}
          onChange={(v) => updateItem(record.id, 'actual_value', v)}
          min={0} step={0.01} size="small" style={{ width: 130 }} />
      ) : val ? `${Number(val).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн` : '—',
    },
    {
      title: 'Різниця', dataIndex: 'difference', key: 'diff', width: 120,
      responsive: ['md' as const],
      render: (v: string) => {
        const num = Number(v)
        const color = num < 0 ? 'red' : num > 0 ? 'green' : undefined
        return <span style={{ color }}>{num.toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн</span>
      },
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/inventories')}>
          До списку
        </Button>
        <ExportDropdownButton
          url={`/documents/inventory/${id}/report/`}
          baseFilename={`inventory_${id}`}
          label="Друк опису"
        />
        {isEditable && (
          <Button icon={<ScanOutlined />} type="primary" onClick={startScanner}>
            Сканувати QR
          </Button>
        )}
        <Button icon={<PrinterOutlined />} onClick={handlePrintQR}>
          Друк QR-міток
        </Button>
      </Space>

      <Title level={4} style={{ fontSize: 18 }}>Інвентаризація №{inventory.number}</Title>

      {/* Summary cards */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={8}>
          <Card size="small">
            <Statistic title="Всього" value={totalItems} valueStyle={{ fontSize: 20 }} />
          </Card>
        </Col>
        <Col xs={8}>
          <Card size="small">
            <Statistic title="Знайдено" value={foundCount}
              valueStyle={{ fontSize: 20, color: '#3f8600' }}
              prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={8}>
          <Card size="small">
            <Statistic title="Нестачі" value={shortages}
              valueStyle={{ fontSize: 20, color: shortages > 0 ? '#cf1322' : undefined }}
              prefix={shortages > 0 ? <CloseCircleOutlined /> : undefined} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions bordered size="small" column={{ xs: 1, sm: 2 }}>
          <Descriptions.Item label="Номер">{inventory.number}</Descriptions.Item>
          <Descriptions.Item label="Статус">
            <Tag color={STATUS_COLORS[inventory.status]}>{inventory.status_display}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Дата">{dayjs(inventory.date).format('DD.MM.YYYY')}</Descriptions.Item>
          <Descriptions.Item label="Наказ">
            №{inventory.order_number} від {dayjs(inventory.order_date).format('DD.MM.YYYY')}
          </Descriptions.Item>
          <Descriptions.Item label="Голова комісії">{inventory.commission_head_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="Місце">{inventory.location || '—'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Table
        dataSource={items}
        columns={columns}
        rowKey="id"
        size="small"
        pagination={false}
        scroll={{ x: 800 }}
      />

      {/* QR Scanner Modal */}
      <Modal
        title="Сканування QR-кодів"
        open={scannerOpen}
        onCancel={stopScanner}
        footer={[<Button key="close" onClick={stopScanner}>Закрити</Button>]}
        width={420}
        destroyOnHidden
        centered
      >
        <div style={{ textAlign: 'center' }}>
          <div id="qr-reader" ref={videoRef} style={{ width: '100%', marginBottom: 16 }} />

          {scanStatus === 'found' && (
            <Alert message="Знайдено та відмічено!" description={scanAssetName}
              type="success" showIcon style={{ marginBottom: 12 }} />
          )}
          {scanStatus === 'already' && (
            <Alert message="Вже зареєстровано" description={scanAssetName}
              type="info" showIcon style={{ marginBottom: 12 }} />
          )}
          {scanStatus === 'not_found' && (
            <Alert message="Не в інвентаризації" description={`Інв. номер: ${scanAssetName}`}
              type="warning" showIcon style={{ marginBottom: 12 }} />
          )}

          <div style={{ marginTop: 12 }}>
            <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
              Або введіть інвентарний номер вручну:
            </Text>
            <Input.Search
              placeholder="Інвентарний номер"
              enterButton="Знайти"
              onSearch={handleManualInput}
              style={{ maxWidth: 300 }}
            />
          </div>

          <div style={{ marginTop: 16, padding: '8px 0', borderTop: '1px solid #f0f0f0' }}>
            <Space>
              <Badge status="success" text={`Знайдено: ${foundCount}`} />
              <Badge status="error" text={`Нестачі: ${shortages}`} />
            </Space>
          </div>
        </div>
      </Modal>
    </div>
  )
}

export default InventoryDetailPage
