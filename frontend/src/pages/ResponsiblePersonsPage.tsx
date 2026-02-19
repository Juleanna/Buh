import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Switch, Select,
  Space, Tag, Popconfirm,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { ResponsiblePerson, Location, Position, PaginatedResponse } from '../types'

const { Title } = Typography

const ResponsiblePersonsPage: React.FC = () => {
  const [persons, setPersons] = useState<ResponsiblePerson[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()
  const [locations, setLocations] = useState<Location[]>([])
  const [positions, setPositions] = useState<Position[]>([])

  const loadPersons = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<ResponsiblePerson>>('/assets/responsible-persons/', { params })
    setPersons(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  const loadLocations = async () => {
    try {
      const { data } = await api.get<PaginatedResponse<Location>>('/assets/locations/', { params: { page_size: 1000 } })
      setLocations(data.results)
    } catch {
      setLocations([])
    }
  }

  const loadPositions = async () => {
    try {
      const { data } = await api.get<PaginatedResponse<Position>>('/assets/positions/', { params: { page_size: 1000, is_active: true } })
      setPositions(data.results)
    } catch {
      setPositions([])
    }
  }

  useEffect(() => {
    loadPersons()
    loadLocations()
    loadPositions()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await api.put(`/assets/responsible-persons/${editingId}/`, values)
        message.success('МВО оновлено')
      } else {
        await api.post('/assets/responsible-persons/', values)
        message.success('МВО створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadPersons()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = (person: ResponsiblePerson) => {
    setEditingId(person.id)
    form.setFieldsValue(person)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/responsible-persons/${id}/`)
      message.success('МВО видалено')
      loadPersons()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  const columns = [
    { title: 'ПІП', dataIndex: 'full_name', key: 'full_name', ellipsis: true },
    { title: 'ІПН', dataIndex: 'ipn', key: 'ipn', width: 120 },
    { title: 'Посада', dataIndex: 'position_name', key: 'position_name', ellipsis: true },
    { title: 'Місцезнаходження', dataIndex: 'location_name', key: 'location_name', ellipsis: true },
    { title: 'К-ть ОЗ', dataIndex: 'assets_count', key: 'assets_count', width: 100 },
    {
      title: 'Співробітник',
      dataIndex: 'is_employee',
      key: 'is_employee',
      width: 120,
      render: (v: boolean) => (
        <Tag color={v ? 'blue' : 'default'}>{v ? 'Так' : 'Ні'}</Tag>
      ),
    },
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
      render: (_: unknown, record: ResponsiblePerson) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити МВО?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Матеріально відповідальні особи</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Нова МВО
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за ПІП або ІПН..."
        onSearch={(v) => { setSearch(v); setPage(1); loadPersons(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={persons}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadPersons(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати МВО' : 'Нова МВО'}
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
          initialValues={{ is_active: true, is_employee: false }}
        >
          <Form.Item name="full_name" label="ПІП" rules={[{ required: true, message: 'Введіть ПІП' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="ipn" label="ІПН" rules={[{ required: true, message: 'Введіть ІПН' }]}>
            <Input maxLength={10} />
          </Form.Item>
          <Form.Item name="position" label="Посада">
            <Select allowClear placeholder="Оберіть посаду" showSearch optionFilterProp="label">
              {positions.map((pos) => (
                <Select.Option key={pos.id} value={pos.id}>{pos.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="location" label="Місцезнаходження">
            <Select allowClear placeholder="Оберіть місцезнаходження">
              {locations.map((loc) => (
                <Select.Option key={loc.id} value={loc.id}>{loc.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="is_employee" label="Співробітник" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="is_active" label="Активна" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ResponsiblePersonsPage
