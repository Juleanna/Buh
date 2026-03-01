import React, { useState, useEffect } from 'react'
import { Layout, Menu, Button, Dropdown, Space, Typography, Badge } from 'antd'
import {
  DashboardOutlined,
  DatabaseOutlined,
  PlusCircleOutlined,
  MinusCircleOutlined,
  CalculatorOutlined,
  AuditOutlined,
  TeamOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  AppstoreOutlined,
  BookOutlined,
  SwapOutlined,
  ToolOutlined,
  SendOutlined,
  BellOutlined,
  FileSearchOutlined,
  BankOutlined,
  EnvironmentOutlined,
  IdcardOutlined,
  TableOutlined,
  FolderOpenOutlined,
  SaveOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../api/client'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  useEffect(() => {
    const loadUnread = () => {
      api.get('/assets/notifications/unread_count/').then((res) => {
        setUnreadCount(res.data.count)
      }).catch(() => {})
    }
    loadUnread()
    const interval = setInterval(loadUnread, 60000)
    return () => clearInterval(interval)
  }, [])

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Головна',
    },
    {
      key: 'assets-sub',
      icon: <DatabaseOutlined />,
      label: 'Основні засоби',
      children: [
        { key: '/assets', icon: <DatabaseOutlined />, label: 'Реєстр ОЗ' },
        { key: '/groups', icon: <AppstoreOutlined />, label: 'Групи ОЗ' },
      ],
    },
    {
      key: 'operations-sub',
      icon: <SwapOutlined />,
      label: 'Операції',
      children: [
        { key: '/receipts', icon: <PlusCircleOutlined />, label: 'Прихід' },
        { key: '/disposals', icon: <MinusCircleOutlined />, label: 'Вибуття' },
        { key: '/revaluations', icon: <SwapOutlined />, label: 'Переоцінки' },
        { key: '/improvements', icon: <ToolOutlined />, label: 'Поліпшення' },
        { key: '/transfers', icon: <SendOutlined />, label: 'Переміщення' },
      ],
    },
    {
      key: '/depreciation',
      icon: <CalculatorOutlined />,
      label: 'Амортизація',
    },
    {
      key: '/entries',
      icon: <BookOutlined />,
      label: 'Проводки',
    },
    {
      key: '/inventories',
      icon: <AuditOutlined />,
      label: 'Інвентаризація',
    },
    {
      key: '/turnover-report',
      icon: <TableOutlined />,
      label: 'Оборотна відомість',
    },
    {
      key: 'directories-sub',
      icon: <FolderOpenOutlined />,
      label: 'Довідники',
      children: [
        { key: '/organizations', icon: <BankOutlined />, label: 'Організації' },
        { key: '/responsible-persons', icon: <IdcardOutlined />, label: 'МВО' },
        { key: '/positions', icon: <TeamOutlined />, label: 'Посади' },
        { key: '/locations', icon: <EnvironmentOutlined />, label: 'Місцезнаходження' },
      ],
    },
    {
      key: '/audit-log',
      icon: <FileSearchOutlined />,
      label: 'Журнал аудиту',
    },
    {
      key: '/notifications',
      icon: <BellOutlined />,
      label: 'Сповіщення',
    },
    ...(user?.role === 'admin' ? [
      {
        key: '/users',
        icon: <TeamOutlined />,
        label: 'Користувачі',
      },
      {
        key: '/backup',
        icon: <SaveOutlined />,
        label: 'Резервна копія',
      },
    ] : []),
  ]

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: 'Профіль' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Вийти', danger: true },
  ]

  const handleUserMenu = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout()
      navigate('/login')
    } else if (key === 'profile') {
      navigate('/profile')
    }
  }

  const roleLabels: Record<string, string> = {
    admin: 'Адміністратор',
    accountant: 'Бухгалтер',
    inventory_manager: 'Інвентаризатор',
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        breakpoint="lg"
        width={240}
        style={{ background: '#fff' }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Text strong style={{ fontSize: collapsed ? 14 : 18, color: '#1677ff' }}>
            {collapsed ? 'ОЗ' : 'Облік ОЗ'}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={collapsed ? [] : ['assets-sub', 'operations-sub', 'directories-sub']}
          items={menuItems}
          onClick={({ key }) => {
            if (!key.endsWith('-sub')) navigate(key)
          }}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #f0f0f0',
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
          <Space>
            <Badge count={unreadCount} size="small">
              <Button
                type="text"
                icon={<BellOutlined />}
                onClick={() => navigate('/notifications')}
              />
            </Badge>
            <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenu }}>
              <Button type="text">
                <Space>
                  <UserOutlined />
                  <span>{user?.full_name || user?.username}</span>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    ({roleLabels[user?.role || ''] || ''})
                  </Text>
                </Space>
              </Button>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
