import React, { useState, useMemo } from 'react'
import {
  Table, Button, Typography, Card, Row, Col, DatePicker,
  Space,
} from 'antd'
import { message } from '../utils/globalMessage'
import { DownloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import api from '../api/client'
import { ExportDropdownButton } from '../components/ExportButton'
import type { TurnoverRow } from '../types'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title } = Typography
const { RangePicker } = DatePicker

const TurnoverReportPage: React.FC = () => {
  const [rows, setRows] = useState<TurnoverRow[]>([])
  const [loading, setLoading] = useState(false)
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null)

  const getParams = () => {
    if (!dateRange) return null
    return {
      date_from: dateRange[0].format('YYYY-MM-DD'),
      date_to: dateRange[1].format('YYYY-MM-DD'),
    }
  }

  const loadData = async () => {
    const params = getParams()
    if (!params) {
      message.warning('Оберіть період')
      return
    }
    setLoading(true)
    try {
      const { data } = await api.get<TurnoverRow[]>('/reports/turnover-statement/', { params })
      setRows(data)
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка завантаження звіту')
    } finally {
      setLoading(false)
    }
  }

  const formatAmount = (v: string) =>
    Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })

  const _s = (field: keyof TurnoverRow) => (a: TurnoverRow, b: TurnoverRow) => (String(a[field] ?? '')).localeCompare(String(b[field] ?? ''))
  const _n = (field: keyof TurnoverRow) => (a: TurnoverRow, b: TurnoverRow) => Number(a[field] || 0) - Number(b[field] || 0)

  const baseColumns = useMemo(() => [
    { title: '№ з/п', dataIndex: 'index', key: 'index', width: 60, sorter: _n('index') },
    { title: 'МВО', dataIndex: 'responsible_person_name', key: 'responsible_person_name', ellipsis: true, width: 160, sorter: _s('responsible_person_name') },
    { title: 'Рахунок', dataIndex: 'account_number', key: 'account_number', width: 100, sorter: _s('account_number') },
    { title: 'Найменування', dataIndex: 'name', key: 'name', ellipsis: true, width: 180, sorter: _s('name') },
    { title: 'Інв. номер', dataIndex: 'inventory_number', key: 'inventory_number', width: 120, sorter: _s('inventory_number') },
    { title: 'Од. виміру', dataIndex: 'unit_of_measure', key: 'unit_of_measure', width: 90, sorter: _s('unit_of_measure') },
    {
      title: 'Вартість',
      dataIndex: 'cost',
      key: 'cost',
      width: 120,
      sorter: _n('cost'),
      render: (v: string) => formatAmount(v),
    },
    {
      title: 'Залишок на початок',
      children: [
        { title: 'к-ть', dataIndex: 'opening_qty', key: 'opening_qty', width: 60, sorter: _n('opening_qty') },
        {
          title: 'сума',
          dataIndex: 'opening_amount',
          key: 'opening_amount',
          width: 120,
          sorter: _n('opening_amount'),
          render: (v: string) => formatAmount(v),
        },
      ],
    },
    {
      title: 'Оборот дебет',
      children: [
        { title: 'к-ть', dataIndex: 'debit_qty', key: 'debit_qty', width: 60, sorter: _n('debit_qty') },
        {
          title: 'сума',
          dataIndex: 'debit_amount',
          key: 'debit_amount',
          width: 120,
          sorter: _n('debit_amount'),
          render: (v: string) => formatAmount(v),
        },
      ],
    },
    {
      title: 'Оборот кредит',
      children: [
        { title: 'к-ть', dataIndex: 'credit_qty', key: 'credit_qty', width: 60, sorter: _n('credit_qty') },
        {
          title: 'сума',
          dataIndex: 'credit_amount',
          key: 'credit_amount',
          width: 120,
          sorter: _n('credit_amount'),
          render: (v: string) => formatAmount(v),
        },
      ],
    },
    {
      title: 'Залишок на кінець',
      children: [
        { title: 'к-ть', dataIndex: 'closing_qty', key: 'closing_qty', width: 60, sorter: _n('closing_qty') },
        {
          title: 'сума',
          dataIndex: 'closing_amount',
          key: 'closing_amount',
          width: 120,
          sorter: _n('closing_amount'),
          render: (v: string) => formatAmount(v),
        },
      ],
    },
  ], [])

  const { columns, components } = useResizableColumns(baseColumns)

  return (
    <div>
      <Title level={4}>Оборотна відомість</Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <span>Період:</span>
              <RangePicker
                value={dateRange}
                onChange={(dates) => setDateRange(dates as [Dayjs, Dayjs] | null)}
                format="DD.MM.YYYY"
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={loadData}
              loading={loading}
            >
              Завантажити
            </Button>
          </Col>
          <Col>
            <ExportDropdownButton
              url={`/documents/turnover-statement/?date_from=${dateRange?.[0]?.format('YYYY-MM-DD') || ''}&date_to=${dateRange?.[1]?.format('YYYY-MM-DD') || ''}`}
              baseFilename="turnover_statement"
              label="Завантажити"
            />
          </Col>
        </Row>
      </Card>

      <Table
        dataSource={rows}
        columns={columns}
        components={components}
        rowKey={(record) => `${record.index}_${record.inventory_number || ''}`}
        loading={loading}
        pagination={false}
        size="small"
        bordered
        scroll={{ x: 1400 }}
      />
    </div>
  )
}

export default TurnoverReportPage
