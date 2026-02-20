import React, { useEffect, useState, useMemo } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Switch,
  Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { Position, PaginatedResponse } from '../types'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title } = Typography

const PositionsPage: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadPositions = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<Position>>('/assets/positions/', { params: { page: p } })
    setPositions(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadPositions()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await api.put(`/assets/positions/${editingId}/`, values)
        message.success('Посаду оновлено')
      } else {
        await api.post('/assets/positions/', values)
        message.success('Посаду створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadPositions()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = (position: Position) => {
    setEditingId(position.id)
    form.setFieldsValue(position)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/positions/${id}/`)
      message.success('Посаду видалено')
      loadPositions()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const baseColumns = useMemo(() => [
    { title: 'Назва', dataIndex: 'name', key: 'name', ellipsis: true, sorter: (a: Position, b: Position) => (a.name || '').localeCompare(b.name || '') },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'status',
      width: 120,
      sorter: (a: Position, b: Position) => Number(a.is_active) - Number(b.is_active),
      render: (v: boolean) => (
        <Tag color={v ? 'green' : 'red'}>{v ? 'Активна' : 'Неактивна'}</Tag>
      ),
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: Position) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити посаду?" onConfirm={() => handleDelete(record.id)}>
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
        <Title level={4} style={{ margin: 0 }}>Посади</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нова посада
        </Button>
      </div>

      <Table
        dataSource={positions}
        columns={columns}
        components={components}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadPositions(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати посаду' : 'Нова посада'}
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
          <Form.Item name="name" label="Назва" rules={[{ required: true, message: 'Введіть назву посади' }]}>
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

export default PositionsPage
