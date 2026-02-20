import React, { useEffect, useState, useMemo } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import AsyncSelect from '../components/AsyncSelect'
import type { Asset, AssetRevaluation, PaginatedResponse } from '../types'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title } = Typography

const assetMapOption = (a: Asset) => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` })

const RevaluationsPage: React.FC = () => {
  const [revaluations, setRevaluations] = useState<AssetRevaluation[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadRevaluations = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<AssetRevaluation>>('/assets/revaluations/', { params })
    setRevaluations(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadRevaluations()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const payload = {
        ...values,
        date: (values.date as dayjs.Dayjs).format('YYYY-MM-DD'),
      }
      if (editingId) {
        await api.put(`/assets/revaluations/${editingId}/`, payload)
        message.success('Переоцінку оновлено')
      } else {
        await api.post('/assets/revaluations/', payload)
        message.success('Переоцінку створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadRevaluations()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
  }

  const handleEdit = (record: AssetRevaluation) => {
    setEditingId(record.id)
    form.setFieldsValue({
      ...record,
      date: dayjs(record.date),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/revaluations/${id}/`)
      message.success('Переоцінку видалено')
      loadRevaluations()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const fmtMoney = (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })

  const baseColumns = useMemo(() => [
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => (a.date || '').localeCompare(b.date || ''),
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true, sorter: (a: AssetRevaluation, b: AssetRevaluation) => (a.asset_name || '').localeCompare(b.asset_name || '') },
    { title: 'Інв.номер', dataIndex: 'asset_inventory_number', key: 'inv', sorter: (a: AssetRevaluation, b: AssetRevaluation) => (a.asset_inventory_number || '').localeCompare(b.asset_inventory_number || '') },
    {
      title: 'Тип',
      dataIndex: 'revaluation_type_display',
      key: 'type',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => (a.revaluation_type_display || '').localeCompare(b.revaluation_type_display || ''),
      render: (text: string, record: AssetRevaluation) => (
        <Tag color={record.revaluation_type === 'upward' ? 'green' : 'red'}>{text}</Tag>
      ),
    },
    {
      title: 'Справедлива вартість',
      dataIndex: 'fair_value',
      key: 'fair_value',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => Number(a.fair_value || 0) - Number(b.fair_value || 0),
      render: fmtMoney,
    },
    {
      title: 'Сума переоцінки',
      dataIndex: 'revaluation_amount',
      key: 'revaluation_amount',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => Number(a.revaluation_amount || 0) - Number(b.revaluation_amount || 0),
      render: fmtMoney,
    },
    {
      title: 'Зал.вартість до',
      dataIndex: 'old_book_value',
      key: 'old_book_value',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => Number(a.old_book_value || 0) - Number(b.old_book_value || 0),
      render: fmtMoney,
    },
    {
      title: 'Зал.вартість після',
      dataIndex: 'new_book_value',
      key: 'new_book_value',
      sorter: (a: AssetRevaluation, b: AssetRevaluation) => Number(a.new_book_value || 0) - Number(b.new_book_value || 0),
      render: fmtMoney,
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: AssetRevaluation) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити переоцінку?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ], [])
  const { columns, components } = useResizableColumns(baseColumns)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Переоцінки основних засобів</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нова переоцінка
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за назвою ОЗ або інв. номером..."
        onSearch={(v) => { setSearch(v); setPage(1); loadRevaluations(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={revaluations}
        columns={columns}
        components={components}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadRevaluations(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати переоцінку ОЗ' : 'Нова переоцінка ОЗ'}
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
              params={{ status: 'active' }}
              mapOption={assetMapOption}
              placeholder="Пошук за номером або назвою"
            />
          </Form.Item>
          <Space size="large">
            <Form.Item name="date" label="Дата переоцінки" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="document_number" label="Номер документа" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="fair_value" label="Справедлива вартість, грн" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RevaluationsPage
