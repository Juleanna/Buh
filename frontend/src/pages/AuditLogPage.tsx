import React, { useEffect, useState, useCallback } from 'react'
import { Table, Typography, Select, Space, Tag } from 'antd'
import dayjs from 'dayjs'
import api from '../api/client'
import type { AuditLogEntry, PaginatedResponse } from '../types'

const { Title } = Typography

const ACTION_OPTIONS = [
  { value: 'create', label: 'Створення' },
  { value: 'update', label: 'Зміна' },
  { value: 'delete', label: 'Видалення' },
  { value: 'receipt', label: 'Оприбуткування' },
  { value: 'disposal', label: 'Вибуття' },
  { value: 'depreciation', label: 'Амортизація' },
  { value: 'revaluation', label: 'Переоцінка' },
  { value: 'improvement', label: 'Поліпшення' },
  { value: 'inventory', label: 'Інвентаризація' },
]

const ACTION_COLORS: Record<string, string> = {
  create: 'green',
  update: 'blue',
  delete: 'red',
  receipt: 'cyan',
  disposal: 'volcano',
  depreciation: 'purple',
  revaluation: 'gold',
  improvement: 'geekblue',
  inventory: 'orange',
}

const AuditLogPage: React.FC = () => {
  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [actionFilter, setActionFilter] = useState<string | undefined>(undefined)

  const loadEntries = useCallback(async (p = page, action = actionFilter) => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page: p }
      if (action) params.action = action
      const { data } = await api.get<PaginatedResponse<AuditLogEntry>>(
        '/assets/audit-log/',
        { params },
      )
      setEntries(data.results)
      setTotal(data.count)
    } finally {
      setLoading(false)
    }
  }, [page, actionFilter])

  useEffect(() => {
    loadEntries()
  }, [])

  const handleActionChange = (value: string | undefined) => {
    setActionFilter(value)
    setPage(1)
    loadEntries(1, value)
  }

  const handlePageChange = (p: number) => {
    setPage(p)
    loadEntries(p)
  }

  const columns = [
    {
      title: 'Час',
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 170,
      render: (value: string) => dayjs(value).format('DD.MM.YYYY HH:mm:ss'),
    },
    {
      title: 'Користувач',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 160,
    },
    {
      title: 'Дія',
      dataIndex: 'action_display',
      key: 'action',
      width: 150,
      render: (text: string, record: AuditLogEntry) => (
        <Tag color={ACTION_COLORS[record.action] || 'default'}>{text}</Tag>
      ),
    },
    {
      title: "Об'єкт",
      dataIndex: 'object_repr',
      key: 'object_repr',
      ellipsis: true,
    },
    {
      title: 'Тип',
      dataIndex: 'content_type_name',
      key: 'content_type_name',
      width: 160,
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Журнал аудиту</Title>
        <Space>
          <Select
            placeholder="Фільтр за дією"
            allowClear
            style={{ width: 220 }}
            value={actionFilter}
            onChange={handleActionChange}
            options={ACTION_OPTIONS}
          />
        </Space>
      </div>

      <Table
        dataSource={entries}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: handlePageChange,
          showTotal: (t) => `Всього: ${t}`,
        }}
        expandable={{
          expandedRowRender: (record: AuditLogEntry) => (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontSize: 13 }}>
              {JSON.stringify(record.changes, null, 2)}
            </pre>
          ),
          rowExpandable: (record: AuditLogEntry) =>
            record.changes !== null &&
            record.changes !== undefined &&
            Object.keys(record.changes).length > 0,
        }}
        scroll={{ x: 1000 }}
      />
    </div>
  )
}

export default AuditLogPage
