import React, { useEffect, useState, useCallback } from 'react'
import { List, Typography, Button, Badge, Tag, Space, Empty } from 'antd'
import { message } from '../utils/globalMessage'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import api from '../api/client'
import type { Notification, PaginatedResponse } from '../types'

dayjs.extend(relativeTime)

const { Title, Text } = Typography

const NotificationsPage: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [unreadCount, setUnreadCount] = useState(0)

  const loadNotifications = useCallback(async (p = page) => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page: p }
      const { data } = await api.get<PaginatedResponse<Notification>>(
        '/assets/notifications/',
        { params },
      )
      setNotifications(data.results)
      setTotal(data.count)
      setUnreadCount(data.results.filter((n) => !n.is_read).length)
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    loadNotifications()
  }, [])

  const handleMarkRead = async (id: number) => {
    try {
      await api.post(`/assets/notifications/${id}/mark_read/`)
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)),
      )
      setUnreadCount((prev) => Math.max(0, prev - 1))
      message.success('Позначено як прочитане')
    } catch {
      message.error('Помилка при оновленні сповіщення')
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await api.post('/assets/notifications/mark_all_read/')
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
      message.success('Всі сповіщення позначено як прочитані')
    } catch {
      message.error('Помилка при оновленні сповіщень')
    }
  }

  const handlePageChange = (p: number) => {
    setPage(p)
    loadNotifications(p)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space size="middle">
          <Title level={4} style={{ margin: 0 }}>Сповіщення</Title>
          {unreadCount > 0 && (
            <Badge count={unreadCount} style={{ backgroundColor: '#1677ff' }} />
          )}
        </Space>
        <Button
          type="primary"
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0}
        >
          Прочитати всі
        </Button>
      </div>

      <List
        loading={loading}
        dataSource={notifications}
        locale={{
          emptyText: <Empty description="Немає сповіщень" />,
        }}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: handlePageChange,
          showTotal: (t) => `Всього: ${t}`,
        }}
        renderItem={(item: Notification) => (
          <List.Item
            style={{
              backgroundColor: item.is_read ? 'transparent' : '#f0f5ff',
              padding: '12px 16px',
              borderRadius: 6,
              marginBottom: 4,
            }}
            actions={[
              item.is_read ? (
                <Text type="secondary" key="read">Прочитано</Text>
              ) : (
                <Button
                  key="mark"
                  type="link"
                  onClick={() => handleMarkRead(item.id)}
                >
                  Позначити прочитаним
                </Button>
              ),
            ]}
          >
            <List.Item.Meta
              title={
                <Space>
                  <Text strong={!item.is_read}>{item.title}</Text>
                  <Tag>{item.notification_type_display}</Tag>
                </Space>
              }
              description={
                <div>
                  <div style={{ marginBottom: 4 }}>{item.message}</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {dayjs(item.created_at).fromNow()}
                  </Text>
                </div>
              }
            />
          </List.Item>
        )}
      />
    </div>
  )
}

export default NotificationsPage
