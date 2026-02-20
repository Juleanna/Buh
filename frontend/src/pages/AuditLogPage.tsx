import React, { useEffect, useState, useCallback } from 'react'
import { Table, Typography, Select, Space, Tag, Descriptions } from 'antd'
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

const CONTENT_TYPE_LABELS: Record<string, string> = {
  asset: 'Основний засіб',
  assetreceipt: 'Прихід ОЗ',
  assetdisposal: 'Вибуття ОЗ',
  assetrevaluation: 'Переоцінка ОЗ',
  assetimprovement: 'Поліпшення ОЗ',
  depreciationrecord: 'Амортизація',
  organization: 'Організація',
  accountentry: 'Проводка',
  assetattachment: 'Документ ОЗ',
  inventoryrecord: 'Інвентаризація',
}

const CHANGE_FIELD_LABELS: Record<string, string> = {
  old_book_value: 'Залишкова вартість (до)',
  new_book_value: 'Залишкова вартість (після)',
  old_initial_cost: 'Початкова вартість (до)',
  new_initial_cost: 'Початкова вартість (після)',
  old_depreciation: 'Знос (до)',
  new_depreciation: 'Знос (після)',
  status: 'Статус',
  amount: 'Сума',
  initial_cost: 'Початкова вартість',
  current_book_value: 'Залишкова вартість',
  accumulated_depreciation: 'Накопичений знос',
  disposal_date: 'Дата вибуття',
  revaluation_amount: 'Сума переоцінки',
  fair_value: 'Справедлива вартість',
  book_value_at_disposal: 'Залишкова вартість при вибутті',
  sale_amount: 'Сума продажу',
  increases_value: 'Збільшує вартість',
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
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.timestamp || '').localeCompare(b.timestamp || ''),
      render: (value: string) => dayjs(value).format('DD.MM.YYYY HH:mm:ss'),
    },
    {
      title: 'Користувач',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 160,
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.user_name || '').localeCompare(b.user_name || ''),
    },
    {
      title: 'Дія',
      dataIndex: 'action_display',
      key: 'action',
      width: 150,
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.action_display || '').localeCompare(b.action_display || ''),
      render: (text: string, record: AuditLogEntry) => (
        <Tag color={ACTION_COLORS[record.action] || 'default'}>{text}</Tag>
      ),
    },
    {
      title: "Об'єкт",
      dataIndex: 'object_repr',
      key: 'object_repr',
      ellipsis: true,
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.object_repr || '').localeCompare(b.object_repr || ''),
    },
    {
      title: 'Тип',
      dataIndex: 'content_type_name',
      key: 'content_type_name',
      width: 160,
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.content_type_name || '').localeCompare(b.content_type_name || ''),
      render: (name: string) => CONTENT_TYPE_LABELS[name] || name,
    },
    {
      title: 'IP',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      sorter: (a: AuditLogEntry, b: AuditLogEntry) => (a.ip_address || '').localeCompare(b.ip_address || ''),
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
            <Descriptions size="small" column={2} bordered>
              {Object.entries(record.changes).map(([key, value]) => (
                <Descriptions.Item label={CHANGE_FIELD_LABELS[key] || key} key={key}>
                  {String(value)}
                </Descriptions.Item>
              ))}
            </Descriptions>
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
