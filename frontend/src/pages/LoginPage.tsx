import React from 'react'
import { Form, Input, Button, Card, Typography, message, Space } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const { Title, Text } = Typography

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const [loading, setLoading] = React.useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('Ласкаво просимо!')
      navigate('/')
    } catch {
      message.error('Невірний логін або пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#f0f2f5',
    }}>
      <Card style={{ width: 400, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        <Space direction="vertical" style={{ width: '100%', textAlign: 'center' }} size="large">
          <div>
            <Title level={3} style={{ marginBottom: 4 }}>Облік основних засобів</Title>
            <Text type="secondary">Увійдіть у систему</Text>
          </div>
          <Form onFinish={onFinish} size="large" style={{ textAlign: 'left' }}>
            <Form.Item
              name="username"
              rules={[{ required: true, message: 'Введіть логін' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="Логін" />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: 'Введіть пароль' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="Пароль" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                Увійти
              </Button>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </div>
  )
}

export default LoginPage
