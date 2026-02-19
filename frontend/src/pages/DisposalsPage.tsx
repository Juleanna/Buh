import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined, CarOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportIconButton } from '../components/ExportButton'
import type { AssetDisposal, Asset, PaginatedResponse } from '../types'

const { Title } = Typography

const DISPOSAL_TYPES = [
  { value: 'sale', label: 'Продаж' },
  { value: 'liquidation', label: 'Ліквідація' },
  { value: 'free_transfer', label: 'Безоплатна передача' },
  { value: 'shortage', label: 'Нестача' },
  { value: 'other', label: 'Інше' },
]

const DisposalsPage: React.FC = () => {
  const [disposals, setDisposals] = useState<AssetDisposal[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadDisposals = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<AssetDisposal>>('/assets/disposals/', { params })
    setDisposals(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadDisposals()
    api.get('/assets/items/', { params: { status: 'active', page_size: 1000 } }).then((res) => {
      setAssets(res.data.results || res.data)
    })
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        document_date: (values.document_date as dayjs.Dayjs).format('YYYY-MM-DD'),
      }
      if (editingId) {
        await api.put(`/assets/disposals/${editingId}/`, payload)
        message.success('Вибуття оновлено')
      } else {
        await api.post('/assets/disposals/', payload)
        message.success('Вибуття оформлено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadDisposals()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
  }

  const handleEdit = (record: AssetDisposal) => {
    setEditingId(record.id)
    form.setFieldsValue({
      ...record,
      document_date: dayjs(record.document_date),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/disposals/${id}/`)
      message.success('Вибуття видалено')
      loadDisposals()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
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
    {
      title: 'Тип вибуття',
      dataIndex: 'disposal_type_display',
      key: 'type',
      render: (text: string) => <Tag>{text}</Tag>,
    },
    {
      title: 'Залишкова вартість',
      dataIndex: 'book_value_at_disposal',
      key: 'book',
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
    },
    {
      title: 'Сума продажу',
      dataIndex: 'sale_amount',
      key: 'sale',
      render: (v: string) => Number(v) > 0
        ? `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`
        : '—',
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: AssetDisposal) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити вибуття?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
          <ExportIconButton
            url={`/documents/disposal/${record.id}/act/`}
            baseFilename={`disposal_act_${record.document_number}`}
            tooltip="Акт ОЗ-3"
          />
          <ExportIconButton
            url={`/documents/disposal/${record.id}/vehicle-act/`}
            baseFilename={`vehicle_disposal_${record.document_number}`}
            tooltip="Акт ОЗ-4"
            icon={<CarOutlined />}
          />
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Вибуття основних засобів</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }} danger>
          Оформити вибуття
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за номером документа або назвою ОЗ..."
        onSearch={(v) => { setSearch(v); setPage(1); loadDisposals(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={disposals}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadDisposals(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати вибуття ОЗ' : 'Вибуття ОЗ'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        okText="Оформити"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="asset" label="Основний засіб" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" placeholder="Оберіть ОЗ"
              options={assets.map(a => ({
                value: a.id,
                label: `${a.inventory_number} — ${a.name} (${Number(a.current_book_value).toLocaleString('uk-UA')} грн)`,
              }))}
            />
          </Form.Item>
          <Form.Item name="disposal_type" label="Тип вибуття" rules={[{ required: true }]}>
            <Select options={DISPOSAL_TYPES} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="document_number" label="Номер документа" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="document_date" label="Дата документа" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
          <Form.Item name="reason" label="Причина вибуття" rules={[{ required: true }]}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="sale_amount" label="Сума продажу, грн (якщо продаж)">
            <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default DisposalsPage
