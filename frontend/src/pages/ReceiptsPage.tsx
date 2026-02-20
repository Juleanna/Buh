import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, Space, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportIconButton } from '../components/ExportButton'
import AsyncSelect from '../components/AsyncSelect'
import type { Asset, AssetReceipt, Organization, PaginatedResponse } from '../types'

const orgMapOption = (o: Organization) => ({ value: o.id, label: `${o.name} (${o.edrpou})` })

const { Title } = Typography

const RECEIPT_TYPES = [
  { value: 'purchase', label: 'Придбання' },
  { value: 'free_receipt', label: 'Безоплатне отримання' },
  { value: 'contribution', label: 'Внесок до статутного капіталу' },
  { value: 'exchange', label: 'Обмін' },
  { value: 'self_made', label: 'Виготовлення власними силами' },
  { value: 'other', label: 'Інше' },
]

const assetMapOption = (a: Asset) => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` })

const ReceiptsPage: React.FC = () => {
  const [receipts, setReceipts] = useState<AssetReceipt[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadReceipts = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<AssetReceipt>>('/assets/receipts/', { params })
    setReceipts(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadReceipts()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        document_date: (values.document_date as dayjs.Dayjs).format('YYYY-MM-DD'),
      }
      if (editingId) {
        await api.put(`/assets/receipts/${editingId}/`, payload)
        message.success('Прихід оновлено')
      } else {
        await api.post('/assets/receipts/', payload)
        message.success('Прихід створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadReceipts()
    } catch (err: any) {
      message.error(err.response?.data?.asset?.[0] || err.response?.data?.detail || 'Помилка')
    }
  }

  const handleEdit = (record: AssetReceipt) => {
    setEditingId(record.id)
    form.setFieldsValue({
      ...record,
      document_date: dayjs(record.document_date),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/receipts/${id}/`)
      message.success('Прихід видалено')
      loadReceipts()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const columns = [
    { title: 'Номер документа', dataIndex: 'document_number', key: 'doc', sorter: (a: AssetReceipt, b: AssetReceipt) => (a.document_number || '').localeCompare(b.document_number || '') },
    {
      title: 'Дата',
      dataIndex: 'document_date',
      key: 'date',
      sorter: (a: AssetReceipt, b: AssetReceipt) => (a.document_date || '').localeCompare(b.document_date || ''),
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true, sorter: (a: AssetReceipt, b: AssetReceipt) => (a.asset_name || '').localeCompare(b.asset_name || '') },
    { title: 'Інв. номер', dataIndex: 'asset_inventory_number', key: 'inv', sorter: (a: AssetReceipt, b: AssetReceipt) => (a.asset_inventory_number || '').localeCompare(b.asset_inventory_number || '') },
    { title: 'Тип', dataIndex: 'receipt_type_display', key: 'type', sorter: (a: AssetReceipt, b: AssetReceipt) => (a.receipt_type_display || '').localeCompare(b.receipt_type_display || '') },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      key: 'amount',
      sorter: (a: AssetReceipt, b: AssetReceipt) => Number(a.amount || 0) - Number(b.amount || 0),
      render: (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }),
    },
    {
      title: 'Постачальник',
      key: 'supplier',
      ellipsis: true,
      sorter: (a: AssetReceipt, b: AssetReceipt) => (a.supplier_organization_name || a.supplier || '').localeCompare(b.supplier_organization_name || b.supplier || ''),
      render: (_: unknown, r: AssetReceipt) =>
        r.supplier_organization_name || r.supplier || '\u2014',
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: AssetReceipt) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити прихід?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
          <ExportIconButton
            url={`/documents/receipt/${record.id}/act/`}
            baseFilename={`receipt_act_${record.document_number}`}
            tooltip="Акт ОЗ-1"
          />
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Прихід основних засобів</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Новий прихід
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за номером документа або постачальником..."
        onSearch={(v) => { setSearch(v); setPage(1); loadReceipts(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={receipts}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadReceipts(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати прихід ОЗ' : 'Новий прихід ОЗ'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="asset" label="Основний засіб" rules={[{ required: true }]}>
            <AsyncSelect
              url="/assets/items/"
              params={{ status: 'active', no_receipt: 1 }}
              mapOption={assetMapOption}
              placeholder="Пошук за номером або назвою"
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
          <Form.Item name="supplier_organization" label="Постачальник / джерело">
            <AsyncSelect url="/assets/organizations/"
              params={{ is_active: true, is_own: false }}
              mapOption={orgMapOption} allowClear placeholder="Пошук контрагента" />
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
