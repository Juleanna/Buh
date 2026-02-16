import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, message, Space, Tag, Popconfirm, Tooltip,
} from 'antd'
import {
  PlusOutlined, EyeOutlined, PlayCircleOutlined,
  CheckCircleOutlined, FilePdfOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { downloadPdf } from '../utils/downloadPdf'
import type { Inventory, User, PaginatedResponse } from '../types'

const { Title } = Typography

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
}

const InventoriesPage: React.FC = () => {
  const navigate = useNavigate()
  const [inventories, setInventories] = useState<Inventory[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadInventories = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<Inventory>>('/assets/inventories/', { params: { page: p } })
    setInventories(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadInventories()
    api.get('/auth/users/').then((res) => {
      setUsers(res.data.results || res.data)
    }).catch(() => {})
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      await api.post('/assets/inventories/', {
        ...values,
        date: (values.date as dayjs.Dayjs).format('YYYY-MM-DD'),
        order_date: (values.order_date as dayjs.Dayjs).format('YYYY-MM-DD'),
      })
      message.success('Інвентаризацію створено')
      setModalOpen(false)
      form.resetFields()
      loadInventories()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
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
    { title: 'Місце', dataIndex: 'location', key: 'location', ellipsis: true },
    { title: 'Позицій', dataIndex: 'items_count', key: 'items', width: 90 },
    {
      title: 'Дії',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: Inventory) => (
        <Space size="small">
          <Tooltip title="Переглянути">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/inventories/${record.id}`)} />
          </Tooltip>
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
          <Tooltip title="PDF">
            <Button size="small" icon={<FilePdfOutlined />}
              onClick={() => downloadPdf(`/documents/inventory/${record.id}/report/`, `inventory_${record.number}.pdf`)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Інвентаризація</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Нова інвентаризація
        </Button>
      </div>

      <Table
        dataSource={inventories}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadInventories(p) },
        }}
        size="small"
      />

      <Modal
        title="Нова інвентаризація"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Створити"
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
            <Select allowClear placeholder="Оберіть голову комісії"
              options={users.map(u => ({ value: u.id, label: u.full_name || u.username }))}
            />
          </Form.Item>
          <Form.Item name="commission_members" label="Члени комісії">
            <Select mode="multiple" placeholder="Оберіть членів комісії"
              options={users.map(u => ({ value: u.id, label: u.full_name || u.username }))}
            />
          </Form.Item>
          <Form.Item name="location" label="Місце проведення">
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

export default InventoriesPage
