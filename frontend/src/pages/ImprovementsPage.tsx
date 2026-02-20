import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import AsyncSelect from '../components/AsyncSelect'
import type { Asset, AssetImprovement, PaginatedResponse } from '../types'

const { Title } = Typography

const IMPROVEMENT_TYPES = [
  { value: 'capital', label: 'Капітальний ремонт' },
  { value: 'current', label: 'Поточний ремонт' },
  { value: 'modernization', label: 'Модернізація' },
  { value: 'reconstruction', label: 'Реконструкція' },
]

const assetMapOption = (a: Asset) => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` })

const ImprovementsPage: React.FC = () => {
  const [improvements, setImprovements] = useState<AssetImprovement[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadImprovements = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<AssetImprovement>>('/assets/improvements/', { params })
    setImprovements(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadImprovements()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        date: (values.date as dayjs.Dayjs).format('YYYY-MM-DD'),
      }
      if (editingId) {
        await api.put(`/assets/improvements/${editingId}/`, payload)
        message.success('Поліпшення оновлено')
      } else {
        await api.post('/assets/improvements/', payload)
        message.success('Поліпшення створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadImprovements()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
  }

  const handleEdit = (record: AssetImprovement) => {
    setEditingId(record.id)
    form.setFieldsValue({
      ...record,
      date: dayjs(record.date),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/improvements/${id}/`)
      message.success('Поліпшення видалено')
      loadImprovements()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const fmtMoney = (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      sorter: (a: AssetImprovement, b: AssetImprovement) => (a.date || '').localeCompare(b.date || ''),
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true, sorter: (a: AssetImprovement, b: AssetImprovement) => (a.asset_name || '').localeCompare(b.asset_name || '') },
    { title: 'Інв.номер', dataIndex: 'asset_inventory_number', key: 'inv', sorter: (a: AssetImprovement, b: AssetImprovement) => (a.asset_inventory_number || '').localeCompare(b.asset_inventory_number || '') },
    { title: 'Тип', dataIndex: 'improvement_type_display', key: 'type', sorter: (a: AssetImprovement, b: AssetImprovement) => (a.improvement_type_display || '').localeCompare(b.improvement_type_display || '') },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      key: 'amount',
      sorter: (a: AssetImprovement, b: AssetImprovement) => Number(a.amount || 0) - Number(b.amount || 0),
      render: fmtMoney,
    },
    { title: 'Виконавець', dataIndex: 'contractor', key: 'contractor', ellipsis: true, sorter: (a: AssetImprovement, b: AssetImprovement) => (a.contractor || '').localeCompare(b.contractor || '') },
    {
      title: 'Збільшує вартість',
      dataIndex: 'increases_value',
      key: 'increases_value',
      sorter: (a: AssetImprovement, b: AssetImprovement) => Number(a.increases_value) - Number(b.increases_value),
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'}>{v ? 'Так' : 'Ні'}</Tag>
      ),
    },
    { title: 'Рах.витрат', dataIndex: 'expense_account', key: 'expense_account', sorter: (a: AssetImprovement, b: AssetImprovement) => (a.expense_account || '').localeCompare(b.expense_account || '') },
    {
      title: 'Дії',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: AssetImprovement) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити поліпшення?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Поліпшення та ремонти ОЗ</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нове поліпшення
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за описом, виконавцем або номером..."
        onSearch={(v) => { setSearch(v); setPage(1); loadImprovements(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={improvements}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadImprovements(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати поліпшення ОЗ' : 'Нове поліпшення ОЗ'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}
          initialValues={{ expense_account: '91' }}
        >
          <Form.Item name="asset" label="Основний засіб" rules={[{ required: true }]}>
            <AsyncSelect
              url="/assets/items/"
              params={{ status: 'active' }}
              mapOption={assetMapOption}
              placeholder="Пошук за номером або назвою"
            />
          </Form.Item>
          <Form.Item name="improvement_type" label="Тип поліпшення" rules={[{ required: true }]}>
            <Select options={IMPROVEMENT_TYPES} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="date" label="Дата" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="document_number" label="Номер документа">
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="Опис робіт">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="amount" label="Сума, грн" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="contractor" label="Виконавець">
            <Input />
          </Form.Item>
          <Space size="large">
            <Form.Item name="increases_value" label="Збільшує вартість" rules={[{ required: true }]}>
              <Select options={[
                { value: true, label: 'Так' },
                { value: false, label: 'Ні' },
              ]} />
            </Form.Item>
            <Form.Item name="expense_account" label="Рахунок витрат">
              <Input />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  )
}

export default ImprovementsPage
