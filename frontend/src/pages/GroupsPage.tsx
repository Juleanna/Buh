import React, { useEffect, useState } from 'react'
import {
  Table, Typography, Tag, Button, Space, Modal, Form, Input,
  InputNumber, Popconfirm, Tooltip,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { AssetGroup } from '../types'

const { Title } = Typography

const GroupsPage: React.FC = () => {
  const [groups, setGroups] = useState<AssetGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadGroups = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/assets/groups/')
      setGroups(data.results || data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadGroups()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      if (editingId) {
        await api.put(`/assets/groups/${editingId}/`, values)
        message.success('Групу оновлено')
      } else {
        await api.post('/assets/groups/', values)
        message.success('Групу створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadGroups()
    } catch (err: any) {
      const detail = err.response?.data
      if (detail && typeof detail === 'object') {
        const msgs = Object.entries(detail).map(([k, v]) =>
          `${k}: ${Array.isArray(v) ? v.join(', ') : v}`
        )
        message.error(msgs.join('; '))
      } else {
        message.error('Помилка збереження')
      }
    }
  }

  const handleEdit = (group: AssetGroup) => {
    setEditingId(group.id)
    form.setFieldsValue(group)
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/groups/${id}/`)
      message.success('Групу видалено')
      loadGroups()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Неможливо видалити групу (є пов\'язані ОЗ)')
    }
  }

  const columns = [
    { title: 'Код', dataIndex: 'code', key: 'code', width: 80, sorter: (a: AssetGroup, b: AssetGroup) => (a.code || '').localeCompare(b.code || '') },
    { title: 'Назва групи', dataIndex: 'name', key: 'name', sorter: (a: AssetGroup, b: AssetGroup) => (a.name || '').localeCompare(b.name || '') },
    {
      title: 'Мін. строк (міс.)',
      dataIndex: 'min_useful_life_months',
      key: 'life',
      width: 150,
      sorter: (a: AssetGroup, b: AssetGroup) => Number(a.min_useful_life_months || 0) - Number(b.min_useful_life_months || 0),
      render: (v: number | null) => v ? `${v} міс. (${Math.round(v / 12)} р.)` : <Tag>Не обмежено</Tag>,
    },
    { title: 'Рахунок обліку', dataIndex: 'account_number', key: 'account', width: 130, sorter: (a: AssetGroup, b: AssetGroup) => (a.account_number || '').localeCompare(b.account_number || '') },
    { title: 'Рахунок зносу', dataIndex: 'depreciation_account', key: 'depr', width: 130, sorter: (a: AssetGroup, b: AssetGroup) => (a.depreciation_account || '').localeCompare(b.depreciation_account || '') },
    { title: 'К-сть ОЗ', dataIndex: 'assets_count', key: 'count', width: 100, sorter: (a: AssetGroup, b: AssetGroup) => Number(a.assets_count || 0) - Number(b.assets_count || 0) },
    {
      title: 'Дії',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: AssetGroup) => (
        <Space size="small">
          <Tooltip title="Редагувати">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm
            title="Видалити групу?"
            description="Видалення можливе лише якщо в групі немає ОЗ"
            onConfirm={() => handleDelete(record.id)}
          >
            <Tooltip title="Видалити">
              <Button size="small" icon={<DeleteOutlined />} danger disabled={(record.assets_count ?? 0) > 0} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Групи основних засобів (згідно ПКУ ст. 138.3.3)</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => {
          setEditingId(null)
          form.resetFields()
          setModalOpen(true)
        }}>
          Додати групу
        </Button>
      </div>

      <Table
        dataSource={groups}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати групу ОЗ' : 'Нова група ОЗ'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        width={600}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Space size="large">
            <Form.Item name="code" label="Код групи" rules={[{ required: true, message: 'Вкажіть код' }]}>
              <Input style={{ width: 120 }} placeholder="Напр. 101" />
            </Form.Item>
            <Form.Item name="name" label="Назва групи" rules={[{ required: true, message: 'Вкажіть назву' }]} style={{ flex: 1 }}>
              <Input placeholder="Напр. Земельні ділянки" style={{ width: 380 }} />
            </Form.Item>
          </Space>
          <Space size="large">
            <Form.Item name="account_number" label="Рахунок обліку" rules={[{ required: true, message: 'Вкажіть рахунок' }]}>
              <Input style={{ width: 150 }} placeholder="Напр. 101" />
            </Form.Item>
            <Form.Item name="depreciation_account" label="Рахунок зносу" rules={[{ required: true, message: 'Вкажіть рахунок' }]}>
              <Input style={{ width: 150 }} placeholder="Напр. 131" />
            </Form.Item>
          </Space>
          <Form.Item name="min_useful_life_months" label="Мінімальний строк корисного використання (місяців)">
            <InputNumber min={0} style={{ width: 250 }} placeholder="Залиште порожнім якщо не обмежено" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default GroupsPage
