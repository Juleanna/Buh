import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import type { AssetImprovement, Asset, PaginatedResponse } from '../types'

const { Title } = Typography

const IMPROVEMENT_TYPES = [
  { value: 'capital', label: 'Капітальний ремонт' },
  { value: 'current', label: 'Поточний ремонт' },
  { value: 'modernization', label: 'Модернізація' },
  { value: 'reconstruction', label: 'Реконструкція' },
]

const ImprovementsPage: React.FC = () => {
  const [improvements, setImprovements] = useState<AssetImprovement[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadImprovements = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<AssetImprovement>>('/assets/improvements/', { params: { page: p } })
    setImprovements(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadImprovements()
    api.get('/assets/items/', { params: { status: 'active', page_size: 1000 } }).then((res) => {
      setAssets(res.data.results || res.data)
    })
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
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true },
    { title: 'Інв.номер', dataIndex: 'asset_inventory_number', key: 'inv' },
    { title: 'Тип', dataIndex: 'improvement_type_display', key: 'type' },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      key: 'amount',
      render: fmtMoney,
    },
    { title: 'Виконавець', dataIndex: 'contractor', key: 'contractor', ellipsis: true },
    {
      title: 'Збільшує вартість',
      dataIndex: 'increases_value',
      key: 'increases_value',
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'}>{v ? 'Так' : 'Ні'}</Tag>
      ),
    },
    { title: 'Рах.витрат', dataIndex: 'expense_account', key: 'expense_account' },
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

      <Table
        dataSource={improvements}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadImprovements(p) },
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
            <Select showSearch optionFilterProp="label" placeholder="Оберіть ОЗ"
              options={assets.map(a => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` }))}
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
