import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Card, Row, Col, InputNumber,
  Space, Statistic, Spin, Tag,
} from 'antd'
import { message } from '../utils/globalMessage'
import { CalculatorOutlined } from '@ant-design/icons'
import api from '../api/client'
import { ExportDropdownButton } from '../components/ExportButton'
import type { DepreciationRecord, PaginatedResponse } from '../types'

const { Title } = Typography

const DepreciationPage: React.FC = () => {
  const [records, setRecords] = useState<DepreciationRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [calcLoading, setCalcLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [summary, setSummary] = useState<{ total_amount: string; records_count: number } | null>(null)
  const [depreciationRate, setDepreciationRate] = useState<number | null>(null)

  const loadRecords = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<DepreciationRecord>>('/assets/depreciation/', {
      params: { page: p, period_year: year, period_month: month },
    })
    setRecords(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  const loadSummary = async () => {
    try {
      const { data } = await api.get('/assets/depreciation/summary/', {
        params: { year, month },
      })
      setSummary(data)
    } catch {
      setSummary(null)
    }
  }

  useEffect(() => {
    loadRecords()
    loadSummary()
  }, [year, month])

  const handleCalculate = async () => {
    setCalcLoading(true)
    try {
      const { data } = await api.post('/assets/depreciation/calculate/', { year, month })
      message.success(`Нараховано амортизацію для ${data.created} ОЗ`)
      if (data.errors?.length > 0) {
        data.errors.forEach((e: { error: string }) => message.warning(e.error))
      }
      loadRecords()
      loadSummary()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка нарахування')
    } finally {
      setCalcLoading(false)
    }
  }

  const fmtNum = (v: string | number) =>
    Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  const columns = [
    { title: 'Субрахунок', dataIndex: 'account_number', key: 'acc', width: 95, align: 'center' as const },
    { title: 'Інвентарний номер', dataIndex: 'asset_inventory_number', key: 'inv', width: 120 },
    { title: 'Назва об\'єкта', dataIndex: 'asset_name', key: 'name', ellipsis: true, width: 180 },
    {
      title: 'Вартість, яка амортизується',
      key: 'depreciable',
      width: 140,
      align: 'right' as const,
      render: (_: unknown, r: DepreciationRecord) =>
        fmtNum(Number(r.asset_initial_cost || 0) - Number(r.asset_residual_value || 0) - Number(r.asset_incoming_depreciation || 0)),
    },
    {
      title: 'Річна сума амортизації',
      key: 'annual',
      width: 130,
      align: 'right' as const,
      render: (_: unknown, r: DepreciationRecord) => {
        if (r.asset_depreciation_rate && Number(r.asset_depreciation_rate) > 0) {
          const depreciable = Number(r.asset_initial_cost || 0) - Number(r.asset_residual_value || 0) - Number(r.asset_incoming_depreciation || 0)
          return fmtNum(depreciable * Number(r.asset_depreciation_rate) / 100)
        }
        return fmtNum(Number(r.amount) * 12)
      },
    },
    {
      title: 'К-ть місяців у періоді',
      dataIndex: 'asset_useful_life_months',
      key: 'months',
      width: 100,
      align: 'center' as const,
    },
    {
      title: 'Сума зносу на початок періоду',
      key: 'wear_start',
      width: 140,
      align: 'right' as const,
      render: (_: unknown, r: DepreciationRecord) =>
        fmtNum(Number(r.asset_initial_cost || 0) - Number(r.book_value_before || 0)),
    },
    {
      title: 'Сума нарахованої амортизації за період',
      dataIndex: 'amount',
      key: 'amount',
      width: 140,
      align: 'right' as const,
      render: (v: string) => <Tag color="blue">{fmtNum(v)}</Tag>,
    },
    {
      title: 'Сума зносу на кінець періоду (гр.7+гр.8)',
      key: 'wear_end',
      width: 150,
      align: 'right' as const,
      render: (_: unknown, r: DepreciationRecord) =>
        fmtNum(Number(r.asset_initial_cost || 0) - Number(r.book_value_after || 0)),
    },
    {
      title: 'Субрахунок витрат',
      dataIndex: 'expense_account',
      key: 'expense',
      width: 100,
      align: 'center' as const,
    },
    {
      title: 'Примітка',
      key: 'note',
      width: 80,
    },
  ]

  return (
    <div>
      <Title level={4}>Розрахунок амортизації основних засобів (крім інших необоротних матеріальних активів)</Title>

      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Space>
              <span>Період:</span>
              <InputNumber
                min={1} max={12} value={month}
                onChange={(v) => v && setMonth(v)}
                style={{ width: 80 }}
              />
              <InputNumber
                min={2000} max={2100} value={year}
                onChange={(v) => v && setYear(v)}
                style={{ width: 100 }}
              />
              <span>Відсоток амортизації:</span>
              <InputNumber
                min={0} max={100} step={0.01}
                value={depreciationRate}
                onChange={(v) => setDepreciationRate(v)}
                placeholder="%"
                style={{ width: 100 }}
                suffix="%"
              />
            </Space>
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<CalculatorOutlined />}
              onClick={handleCalculate}
              loading={calcLoading}
            >
              Нарахувати амортизацію
            </Button>
          </Col>
          <Col>
            <ExportDropdownButton
              url={`/documents/depreciation-report/?year=${year}&month=${month}`}
              baseFilename={`depreciation_${year}_${month}`}
              label="Відомість"
            />
          </Col>
          {summary && (
            <Col flex="auto" style={{ textAlign: 'right' }}>
              <Space size="large">
                <Statistic
                  title="Всього нараховано"
                  value={Number(summary.total_amount)}
                  precision={2}
                  suffix="грн"
                  valueStyle={{ fontSize: 16 }}
                />
                <Statistic
                  title="К-сть записів"
                  value={summary.records_count}
                  valueStyle={{ fontSize: 16 }}
                />
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      <Table
        dataSource={records}
        columns={columns}
        rowKey="id"
        loading={loading}
        bordered
        scroll={{ x: 1500 }}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadRecords(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />
    </div>
  )
}

export default DepreciationPage
