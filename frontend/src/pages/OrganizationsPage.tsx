import React, { useEffect, useState, useMemo } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Switch,
  Space, Tag, Popconfirm, Select,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { Organization, ResponsiblePerson, PaginatedResponse } from '../types'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title } = Typography

const OrganizationsPage: React.FC = () => {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()
  const [persons, setPersons] = useState<ResponsiblePerson[]>([])

  const loadOrganizations = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<Organization>>('/assets/organizations/', { params: { page: p } })
    setOrganizations(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadOrganizations()
    api.get<PaginatedResponse<ResponsiblePerson>>('/assets/responsible-persons/', { params: { page_size: 1000 } })
      .then(res => setPersons(res.data.results))
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

  const baseColumns = useMemo(() => [
    { title: 'Назва', dataIndex: 'name', key: 'name', ellipsis: true, sorter: (a: Organization, b: Organization) => (a.name || '').localeCompare(b.name || '') },
    { title: 'Коротка назва', dataIndex: 'short_name', key: 'short_name', ellipsis: true, sorter: (a: Organization, b: Organization) => (a.short_name || '').localeCompare(b.short_name || '') },
    { title: 'ЄДРПОУ', dataIndex: 'edrpou', key: 'edrpou', width: 120, sorter: (a: Organization, b: Organization) => (a.edrpou || '').localeCompare(b.edrpou || '') },
    { title: 'Директор', dataIndex: 'director_name', key: 'director_name', ellipsis: true, sorter: (a: Organization, b: Organization) => (a.director_name || '').localeCompare(b.director_name || '') },
    { title: 'Гол. бухгалтер', dataIndex: 'accountant_name', key: 'accountant_name', ellipsis: true, sorter: (a: Organization, b: Organization) => (a.accountant_name || '').localeCompare(b.accountant_name || '') },
    {
      title: 'Власна',
      dataIndex: 'is_own',
      key: 'is_own',
      width: 100,
      sorter: (a: Organization, b: Organization) => Number(a.is_own) - Number(b.is_own),
      render: (v: boolean) => v ? <Tag color="blue">Власна</Tag> : null,
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'status',
      width: 120,
      sorter: (a: Organization, b: Organization) => Number(a.is_active) - Number(b.is_active),
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
  ], [])
  const { columns, components } = useResizableColumns(baseColumns)

  const personOptions = persons.map(p => ({
    value: p.id,
    label: p.full_name + (p.position_name ? ` (${p.position_name})` : ''),
  }))

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
        components={components}
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
          initialValues={{ is_active: true, is_own: false }}
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
            <Select
              options={personOptions}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              placeholder="Оберіть директора"
            />
          </Form.Item>
          <Form.Item name="accountant" label="Головний бухгалтер">
            <Select
              options={personOptions}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              placeholder="Оберіть головного бухгалтера"
            />
          </Form.Item>
          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="is_own" label="Власна організація" valuePropName="checked"
            tooltip="Тільки одна організація може бути власною. При позначенні — попередня скидається.">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default OrganizationsPage
