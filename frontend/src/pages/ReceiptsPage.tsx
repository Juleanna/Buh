import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, message, Space, Tooltip,
} from 'antd'
import { PlusOutlined, FilePdfOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import { downloadPdf } from '../utils/downloadPdf'
import type { AssetReceipt, Asset, PaginatedResponse } from '../types'

const { Title } = Typography

const RECEIPT_TYPES = [
  { value: 'purchase', label: 'Придбання' },
  { value: 'free_receipt', label: 'Безоплатне отримання' },
  { value: 'contribution', label: 'Внесок до статутного капіталу' },
  { value: 'exchange', label: 'Обмін' },
  { value: 'self_made', label: 'Виготовлення власними силами' },
  { value: 'other', label: 'Інше' },
]

const ReceiptsPage: React.FC = () => {
  const [receipts, setReceipts] = useState<AssetReceipt[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadReceipts = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<AssetReceipt>>('/assets/receipts/', { params: { page: p } })
    setReceipts(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadReceipts()
    api.get('/assets/items/', { params: { status: 'active', page_size: 1000 } }).then((res) => {
      setAssets(res.data.results || res.data)
    })
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      await api.post('/assets/receipts/', {
        ...values,
        document_date: (values.document_date as dayjs.Dayjs).format('YYYY-MM-DD'),
      })
      message.success('Прихід створено')
      setModalOpen(false)
      form.resetFields()
      loadReceipts()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
  }

  const columns = [
    { title: 'Номер документа', dataIndex: 'document_number', key: 'doc' },
    {
      title: 'Дата',
      dataIndex: 'document_date',
      key: 'date',
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true },
    { title: 'Інв. номер', dataIndex: 'asset_inventory_number', key: 'inv' },
    { title: 'Тип', dataIndex: 'receipt_type_display', key: 'type' },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      key: 'amount',
      render: (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }),
    },
    { title: 'Постачальник', dataIndex: 'supplier', key: 'supplier', ellipsis: true },
    {
      title: 'Дії',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: AssetReceipt) => (
        <Tooltip title="Акт ОЗ-1 (PDF)">
          <Button
            size="small"
            icon={<FilePdfOutlined />}
            onClick={() => downloadPdf(
              `/documents/receipt/${record.id}/act/`,
              `receipt_act_${record.document_number}.pdf`
            )}
          />
        </Tooltip>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Прихід основних засобів</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Новий прихід
        </Button>
      </div>

      <Table
        dataSource={receipts}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadReceipts(p) },
        }}
        size="small"
      />

      <Modal
        title="Новий прихід ОЗ"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="asset" label="Основний засіб" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" placeholder="Оберіть ОЗ"
              options={assets.map(a => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` }))}
            />
          </Form.Item>
          <Form.Item name="receipt_type" label="Тип надходження" rules={[{ required: true }]}>
            <Select options={RECEIPT_TYPES} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="document_number" label="Номер документа" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="document_date" label="Дата документа" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
          <Form.Item name="amount" label="Сума, грн" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="supplier" label="Постачальник / джерело">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ReceiptsPage
