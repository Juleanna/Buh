import React, { useEffect, useState } from 'react'
import {
  Card, Form, Input, Button, Typography, Descriptions, Tag, Select, Space,
  Divider, Row, Col,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  UserOutlined, MailOutlined, PhoneOutlined, LockOutlined, SaveOutlined,
} from '@ant-design/icons'
import api from '../api/client'
import { useAuthStore } from '../store/authStore'
import AsyncSelect from '../components/AsyncSelect'
import type { User, Position, PaginatedResponse } from '../types'

const { Title, Text } = Typography

const ROLE_LABELS: Record<string, string> = {
  admin: 'Адміністратор',
  accountant: 'Бухгалтер',
  inventory_manager: 'Інвентаризатор',
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'red',
  accountant: 'blue',
  inventory_manager: 'green',
}

const posMapOption = (p: Position) => ({ value: p.id, label: p.name })

const ProfilePage: React.FC = () => {
  const { user, loadProfile } = useAuthStore()
  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        first_name: user.first_name,
        last_name: user.last_name,
        patronymic: user.patronymic,
        email: user.email,
        position: user.position,
        phone: user.phone,
      })
    }
  }, [user, profileForm])

  const handleSaveProfile = async (values: Record<string, string>) => {
    setSaving(true)
    try {
      await api.put('/auth/profile/', values)
      message.success('Профіль оновлено')
      await loadProfile()
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
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async (values: { old_password: string; new_password: string }) => {
    setChangingPassword(true)
    try {
      await api.put('/auth/change-password/', values)
      message.success('Пароль успішно змінено')
      passwordForm.resetFields()
    } catch (err: any) {
      const detail = err.response?.data
      if (detail?.old_password) {
        message.error('Невірний поточний пароль')
      } else if (detail && typeof detail === 'object') {
        const msgs = Object.entries(detail).map(([k, v]) =>
          `${k}: ${Array.isArray(v) ? v.join(', ') : v}`
        )
        message.error(msgs.join('; '))
      } else {
        message.error('Помилка зміни пароля')
      }
    } finally {
      setChangingPassword(false)
    }
  }

  if (!user) return null

  return (
    <div>
      <Title level={4}>Профіль користувача</Title>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={8}>
          <Card>
            <div style={{ textAlign: 'center', marginBottom: 16 }}>
              <div style={{
                width: 80, height: 80, borderRadius: '50%',
                background: '#1677ff', display: 'flex', alignItems: 'center',
                justifyContent: 'center', margin: '0 auto 12px',
              }}>
                <UserOutlined style={{ fontSize: 36, color: '#fff' }} />
              </div>
              <Title level={5} style={{ margin: 0 }}>{user.full_name || user.username}</Title>
              <Tag color={ROLE_COLORS[user.role]} style={{ marginTop: 8 }}>
                {ROLE_LABELS[user.role] || user.role}
              </Tag>
            </div>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Логін">{user.username}</Descriptions.Item>
              <Descriptions.Item label="Email">{user.email || '—'}</Descriptions.Item>
              <Descriptions.Item label="Посада">{user.position_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="Телефон">{user.phone || '—'}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card title="Редагувати профіль">
            <Form
              form={profileForm}
              layout="vertical"
              onFinish={handleSaveProfile}
            >
              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Form.Item name="last_name" label="Прізвище" rules={[{ required: true, message: 'Вкажіть прізвище' }]}>
                    <Input prefix={<UserOutlined />} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="first_name" label="Ім'я" rules={[{ required: true, message: "Вкажіть ім'я" }]}>
                    <Input />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="patronymic" label="По батькові">
                    <Input />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item name="email" label="Email" rules={[{ type: 'email', message: 'Невірний формат email' }]}>
                    <Input prefix={<MailOutlined />} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="phone" label="Телефон">
                    <Input prefix={<PhoneOutlined />} placeholder="+380..." />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="position" label="Посада">
                <AsyncSelect url="/assets/positions/" params={{ is_active: true }}
                  mapOption={posMapOption} allowClear placeholder="Пошук посади" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving} icon={<SaveOutlined />}>
                  Зберегти зміни
                </Button>
              </Form.Item>
            </Form>
          </Card>

          <Card title="Змінити пароль" style={{ marginTop: 24 }}>
            <Form
              form={passwordForm}
              layout="vertical"
              onFinish={handleChangePassword}
              style={{ maxWidth: 400 }}
            >
              <Form.Item
                name="old_password"
                label="Поточний пароль"
                rules={[{ required: true, message: 'Введіть поточний пароль' }]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              <Form.Item
                name="new_password"
                label="Новий пароль"
                rules={[
                  { required: true, message: 'Введіть новий пароль' },
                  { min: 8, message: 'Мінімум 8 символів' },
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              <Form.Item
                name="confirm_password"
                label="Підтвердіть новий пароль"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Підтвердіть пароль' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve()
                      }
                      return Promise.reject(new Error('Паролі не збігаються'))
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={changingPassword} danger icon={<LockOutlined />}>
                  Змінити пароль
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default ProfilePage
