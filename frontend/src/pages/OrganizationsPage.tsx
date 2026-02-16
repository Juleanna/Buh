import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Switch,
  message, Space, Tag, Popconfirm,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { Organization, PaginatedResponse } from '../types'

const { Title } = Typography

const OrganizationsPage: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadOrganizations = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<Organization>>('/assets/organizations/', { params: { page: p } })
    setOrganizations(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadOrganizations()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await api.put(`/assets/organizations/${editingId}/`, values)
        message.success('Організацію оновлено')
      } else {
        await api.post('/assets/organizations/', values)
        message.success('Організацію створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadOrganizations()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = (org: Organization) => {
    setEditingId(org.id)
    form.setFieldsValue(org)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/organizations/${id}/`)
      message.success('Організацію видалено')
      loadOrganizations()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const columns = [
    { title: 'Назва', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: 'Коротка назва', dataIndex: 'short_name', key: 'short_name', ellipsis: true },
    { title: 'ЄДРПОУ', dataIndex: 'edrpou', key: 'edrpou', width: 120 },
    { title: 'Директор', dataIndex: 'director', key: 'director', ellipsis: true },
    { title: 'Гол. бухгалтер', dataIndex: 'accountant', key: 'accountant', ellipsis: true },
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
      render: (_: unknown, record: Organization) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити організацію?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Організації</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нова організація
        </Button>
      </div>

      <Table
        dataSource={organizations}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadOrganizations(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати організацію' : 'Нова організація'}
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
          <Form.Item name="name" label="Назва" rules={[{ required: true, message: 'Введіть назву організації' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="short_name" label="Коротка назва">
            <Input />
          </Form.Item>
          <Form.Item name="edrpou" label="ЄДРПОУ" rules={[{ required: true, message: 'Введіть код ЄДРПОУ' }]}>
            <Input maxLength={10} />
          </Form.Item>
          <Form.Item name="address" label="Адреса">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="director" label="Директор">
            <Input />
          </Form.Item>
          <Form.Item name="accountant" label="Головний бухгалтер">
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

export default OrganizationsPage
