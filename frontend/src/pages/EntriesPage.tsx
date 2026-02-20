import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, DatePicker, Select,
  Space, Tag, Card, Statistic, Row, Col,
} from 'antd'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportDropdownButton } from '../components/ExportButton'
import type { AccountEntry, PaginatedResponse } from '../types'

const { Title } = Typography
const { RangePicker } = DatePicker

const ENTRY_TYPES = [
  { value: 'receipt', label: 'Оприбуткування' },
  { value: 'depreciation', label: 'Амортизація' },
  { value: 'disposal', label: 'Вибуття' },
  { value: 'revaluation', label: 'Переоцінка' },
  { value: 'improvement', label: 'Поліпшення' },
  { value: 'repair', label: 'Ремонт' },
]

const ENTRY_TYPE_COLORS: Record<string, string> = {
  receipt: 'green',
  depreciation: 'blue',
  disposal: 'red',
  revaluation: 'purple',
  improvement: 'orange',
  repair: 'cyan',
}

const EntriesPage: React.FC = () => {
  const [entries, setEntries] = useState<AccountEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [entryType, setEntryType] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [totalAmount, setTotalAmount] = useState(0)
  const [postedCount, setPostedCount] = useState(0)

  const loadEntries = async (p = page) => {
    setLoading(true)
    const params: Record<string, unknown> = { page: p }
    if (entryType) {
      params.entry_type = entryType
    }
    if (dateRange) {
      params.date_from = dateRange[0].format('YYYY-MM-DD')
      params.date_to = dateRange[1].format('YYYY-MM-DD')
    }
    const { data } = await api.get<PaginatedResponse<AccountEntry>>('/assets/entries/', { params })
    setEntries(data.results)
    setTotal(data.count)

    // Calculate summary from results
    let sumAmount = 0
    let posted = 0
    data.results.forEach((entry) => {
      sumAmount += Number(entry.amount)
      if (entry.is_posted) posted += 1
    })
    setTotalAmount(sumAmount)
    setPostedCount(posted)

    setLoading(false)
  }

  useEffect(() => {
    setPage(1)
    loadEntries(1)
  }, [entryType, dateRange])

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      width: 110,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.date || '').localeCompare(b.date || ''),
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    {
      title: 'Тип',
      dataIndex: 'entry_type_display',
      key: 'type',
      width: 200,
      ellipsis: true,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.entry_type_display || '').localeCompare(b.entry_type_display || ''),
      render: (text: string, record: AccountEntry) => (
        <Tag color={ENTRY_TYPE_COLORS[record.entry_type] || 'default'}>{text}</Tag>
      ),
    },
    {
      title: 'Дебет',
      dataIndex: 'debit_account',
      key: 'debit',
      width: 100,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.debit_account || '').localeCompare(b.debit_account || ''),
    },
    {
      title: 'Кредит',
      dataIndex: 'credit_account',
      key: 'credit',
      width: 100,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.credit_account || '').localeCompare(b.credit_account || ''),
    },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      sorter: (a: AccountEntry, b: AccountEntry) => Number(a.amount || 0) - Number(b.amount || 0),
      render: (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }),
    },
    {
      title: 'ОЗ',
      dataIndex: 'asset_name',
      key: 'asset',
      ellipsis: true,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.asset_name || '').localeCompare(b.asset_name || ''),
    },
    {
      title: 'Опис',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      sorter: (a: AccountEntry, b: AccountEntry) => (a.description || '').localeCompare(b.description || ''),
    },
    {
      title: 'Статус',
      dataIndex: 'is_posted',
      key: 'status',
      width: 110,
      sorter: (a: AccountEntry, b: AccountEntry) => Number(a.is_posted) - Number(b.is_posted),
      render: (posted: boolean) => (
        <Tag color={posted ? 'green' : 'red'}>
          {posted ? 'Проведено' : 'Не проведено'}
        </Tag>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>Журнал проводок</Title>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <RangePicker
            format="DD.MM.YYYY"
            value={dateRange}
            onChange={(dates) => {
              setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)
            }}
            allowClear
          />
          <Select
            placeholder="Тип операції"
            options={ENTRY_TYPES}
            value={entryType}
            onChange={(v) => setEntryType(v)}
            allowClear
            style={{ width: 200 }}
          />
          <ExportDropdownButton
            url={`/documents/entries-report/?date_from=${dateRange ? dateRange[0].format('YYYY-MM-DD') : ''}&date_to=${dateRange ? dateRange[1].format('YYYY-MM-DD') : ''}`}
            baseFilename="journal-provodok"
            label="Завантажити"
          />
        </Space>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic title="Всього проводок" value={total} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Загальна сума"
              value={totalAmount}
              precision={2}
              suffix="грн"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Проведено"
              value={postedCount}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      <Table
        dataSource={entries}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadEntries(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />
    </div>
  )
}

export default EntriesPage
