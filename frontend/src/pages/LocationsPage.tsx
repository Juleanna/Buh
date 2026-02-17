import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Switch,
  Space, Tag, Popconfirm, Tooltip,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { Location, PaginatedResponse } from '../types'

const { Title } = Typography

const LocationsPage: React.FC = () => {
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadLocations = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<Location>>('/assets/locations/', { params: { page: p } })
    setLocations(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadLocations()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await api.put(`/assets/locations/${editingId}/`, values)
        message.success('Місцезнаходження оновлено')
      } else {
        await api.post('/assets/locations/', values)
        message.success('Місцезнаходження створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadLocations()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = (location: Location) => {
    setEditingId(location.id)
    form.setFieldsValue(location)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/locations/${id}/`)
      message.success('Місцезнаходження видалено')
      loadLocations()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const columns = [
    { title: 'Назва', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: 'К-ть ОЗ', dataIndex: 'assets_count', key: 'assets_count', width: 100 },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'status',
      width: 120,
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'}>{v ? 'Активна' : 'Неактивна'}</Tag>
      ),
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Location) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Tooltip title={record.assets_count && record.assets_count > 0 ? 'Неможливо видалити: є прив\'язані ОЗ' : undefined}>
            <Popconfirm
              title="Видалити місцезнаходження?"
              onConfirm={() => handleDelete(record.id)}
              disabled={!!record.assets_count && record.assets_count > 0}
            >
              <Button
                size="small"
                icon={<DeleteOutlined />}
                danger
                disabled={!!record.assets_count && record.assets_count > 0}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Місцезнаходження</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нове місцезнаходження
        </Button>
      </div>

      <Table
        dataSource={locations}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadLocations(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати місцезнаходження' : 'Нове місцезнаходження'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ is_active: true }}
        >
          <Form.Item name="name" label="Назва" rules={[{ required: true, message: 'Введіть назву' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default LocationsPage
