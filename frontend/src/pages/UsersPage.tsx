import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select, Tag, Space,
} from 'antd'
import { message } from '../utils/globalMessage'
import { PlusOutlined } from '@ant-design/icons'
import api from '../api/client'
import type { User } from '../types'

const { Title } = Typography

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  admin: { label: 'Адміністратор', color: 'red' },
  accountant: { label: 'Бухгалтер', color: 'blue' },
  inventory_manager: { label: 'Інвентаризатор', color: 'green' },
}

const UsersPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadUsers = async () => {
    setLoading(true)
    const { data } = await api.get('/auth/users/')
    setUsers(data.results || data)
    setLoading(false)
  }

  useEffect(() => { loadUsers() }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      await api.post('/auth/register/', values)
      message.success('Користувача створено')
      setModalOpen(false)
      form.resetFields()
      loadUsers()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'object'
        ? Object.values(detail).flat().join(', ')
        : 'Помилка'
      message.error(msg)
    }
  }

  const columns = [
    { title: 'Логін', dataIndex: 'username', key: 'username' },
    { title: 'ПІБ', dataIndex: 'full_name', key: 'name' },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Посада', dataIndex: 'position', key: 'position' },
    {
      title: 'Роль',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const r = ROLE_LABELS[role]
        return r ? <Tag color={r.color}>{r.label}</Tag> : role
      },
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'active',
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Активний' : 'Неактивний'}</Tag>,
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Управління користувачами</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Новий користувач
        </Button>
      </div>

      <Table
        dataSource={users}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={false}
        size="small"
      />

      <Modal
        title="Новий користувач"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Створити"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="username" label="Логін" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, min: 8 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input type="email" />
          </Form.Item>
          <Space size="large">
            <Form.Item name="last_name" label="Прізвище" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="first_name" label="Ім'я" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="patronymic" label="По батькові">
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="role" label="Роль" rules={[{ required: true }]}>
            <Select options={[
              { value: 'admin', label: 'Адміністратор' },
              { value: 'accountant', label: 'Бухгалтер' },
              { value: 'inventory_manager', label: 'Інвентаризатор' },
            ]} />
          </Form.Item>
          <Form.Item name="position" label="Посада">
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Телефон">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default UsersPage
