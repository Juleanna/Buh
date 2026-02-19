import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, Space, Tag, Popconfirm, Tooltip,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  PlusOutlined, EyeOutlined, PlayCircleOutlined,
  CheckCircleOutlined, DeleteOutlined, EditOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportIconButton } from '../components/ExportButton'
import type { Inventory, ResponsiblePerson, PaginatedResponse, Location } from '../types'

const { Title } = Typography

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
}

const InventoriesPage: React.FC = () => {
  const navigate = useNavigate()
  const [inventories, setInventories] = useState<Inventory[]>([])
  const [responsiblePersons, setResponsiblePersons] = useState<ResponsiblePerson[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadInventories = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<Inventory>>('/assets/inventories/', { params })
    setInventories(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadInventories()
    api.get('/assets/responsible-persons/', { params: { is_active: true, is_employee: true, page_size: 1000 } }).then((res) => {
      setResponsiblePersons(res.data.results || res.data)
    }).catch(() => {})
    api.get('/assets/locations/', { params: { is_active: true } }).then((res) => {
      setLocations(res.data.results || res.data)
    }).catch(() => {})
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    const payload = {
      ...values,
      date: (values.date as dayjs.Dayjs).format('YYYY-MM-DD'),
      order_date: (values.order_date as dayjs.Dayjs).format('YYYY-MM-DD'),
    }
    try {
      if (editingId) {
        await api.put(`/assets/inventories/${editingId}/`, payload)
        message.success('Інвентаризацію оновлено')
      } else {
        await api.post('/assets/inventories/', payload)
        message.success('Інвентаризацію створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadInventories()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = async (inventory: Inventory) => {
    setEditingId(inventory.id)
    try {
      const { data } = await api.get(`/assets/inventories/${inventory.id}/`)
      form.setFieldsValue({
        ...data,
        date: dayjs(data.date),
        order_date: dayjs(data.order_date),
      })
    } catch {
      form.setFieldsValue({
        ...inventory,
        date: dayjs(inventory.date),
        order_date: dayjs(inventory.order_date),
      })
    }
    setModalOpen(true)
  }

  const handlePopulate = async (id: number) => {
    try {
      const { data } = await api.post(`/assets/inventories/${id}/populate/`)
      message.success(`Заповнено ${data.created} позицій. Всього: ${data.total}`)
      loadInventories()
    } catch (err: any) {
      message.error(err.response?.data?.error || 'Помилка')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/inventories/${id}/`)
      message.success('Інвентаризацію видалено')
      loadInventories()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const handleComplete = async (id: number) => {
    try {
      const { data } = await api.post(`/assets/inventories/${id}/complete/`)
      message.success(
        `Інвентаризацію завершено. Знайдено: ${data.found}, нестач: ${data.shortages}`
      )
      loadInventories()
    } catch (err: any) {
      message.error(err.response?.data?.error || 'Помилка')
    }
  }

  const columns = [
    { title: '№', dataIndex: 'number', key: 'number', width: 100 },
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      width: 120,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: '№ наказу', dataIndex: 'order_number', key: 'order', width: 120 },
    {
      title: 'Статус',
      dataIndex: 'status_display',
      key: 'status',
      width: 120,
      render: (text: string, record: Inventory) => (
        <Tag color={STATUS_COLORS[record.status]}>{text}</Tag>
      ),
    },
    { title: 'Голова комісії', dataIndex: 'commission_head_name', key: 'head', ellipsis: true },
    { title: 'Місце', dataIndex: 'location_name', key: 'location', ellipsis: true },
    { title: 'Позицій', dataIndex: 'items_count', key: 'items', width: 90 },
    {
      title: 'Дії',
      key: 'actions',
      width: 220,
      render: (_: unknown, record: Inventory) => (
        <Space size="small">
          <Tooltip title="Переглянути">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/inventories/${record.id}`)} />
          </Tooltip>
          {record.status !== 'completed' && (
            <Tooltip title="Редагувати">
              <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
            </Tooltip>
          )}
          {record.status === 'draft' && (
            <Tooltip title="Заповнити ОЗ">
              <Popconfirm title="Заповнити активними ОЗ?" onConfirm={() => handlePopulate(record.id)}>
                <Button size="small" icon={<PlayCircleOutlined />} />
              </Popconfirm>
            </Tooltip>
          )}
          {record.status === 'in_progress' && (
            <Tooltip title="Завершити">
              <Popconfirm title="Завершити інвентаризацію?" onConfirm={() => handleComplete(record.id)}>
                <Button size="small" icon={<CheckCircleOutlined />} type="primary" />
              </Popconfirm>
            </Tooltip>
          )}
          <ExportIconButton
            url={`/documents/inventory/${record.id}/report/`}
            baseFilename={`inventory_${record.number}`}
            tooltip="Інвентаризаційний опис"
          />
          {record.status !== 'completed' && (
            <Tooltip title="Видалити">
              <Popconfirm title="Видалити інвентаризацію?" onConfirm={() => handleDelete(record.id)}>
                <Button size="small" icon={<DeleteOutlined />} danger />
              </Popconfirm>
            </Tooltip>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Інвентаризація</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нова інвентаризація
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за номером або наказом..."
        onSearch={(v) => { setSearch(v); setPage(1); loadInventories(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={inventories}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadInventories(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати інвентаризацію' : 'Нова інвентаризація'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="number" label="Номер інвентаризації" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space size="large">
            <Form.Item name="date" label="Дата інвентаризації" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="order_date" label="Дата наказу" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
          <Form.Item name="order_number" label="Номер наказу" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="commission_head" label="Голова комісії">
            <Select allowClear placeholder="Оберіть голову комісії" showSearch optionFilterProp="label"
              options={responsiblePersons.map(p => ({ value: p.id, label: p.full_name }))}
            />
          </Form.Item>
          <Form.Item name="commission_members" label="Члени комісії">
            <Select mode="multiple" placeholder="Оберіть членів комісії" showSearch optionFilterProp="label"
              options={responsiblePersons.map(p => ({ value: p.id, label: p.full_name }))}
            />
          </Form.Item>
          <Form.Item name="location" label="Місце проведення">
            <Select allowClear placeholder="Оберіть місцезнаходження" showSearch optionFilterProp="label"
              options={locations.map(loc => ({ value: loc.id, label: loc.name }))}
            />
          </Form.Item>
          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default InventoriesPage
