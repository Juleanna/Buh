import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Card, Row, Col, InputNumber,
  message, Space, Statistic, Spin, Tag,
} from 'antd'
import { CalculatorOutlined, FilePdfOutlined } from '@ant-design/icons'
import api from '../api/client'
import { downloadPdf } from '../utils/downloadPdf'
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

  const handleDownloadPdf = () => {
    downloadPdf(`/documents/depreciation-report/?year=${year}&month=${month}`, `depreciation_${year}_${month}.pdf`)
  }

  const columns = [
    { title: 'Інв. номер', dataIndex: 'asset_inventory_number', key: 'inv', width: 120 },
    { title: 'Назва ОЗ', dataIndex: 'asset_name', key: 'name', ellipsis: true },
    { title: 'Метод', dataIndex: 'method_display', key: 'method', width: 180, ellipsis: true },
    {
      title: 'Вартість до',
      dataIndex: 'book_value_before',
      key: 'before',
      width: 140,
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
    },
    {
      title: 'Амортизація',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      render: (v: string) => <Tag color="blue">{Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн</Tag>,
    },
    {
      title: 'Вартість після',
      dataIndex: 'book_value_after',
      key: 'after',
      width: 140,
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
    },
  ]

  return (
    <div>
      <Title level={4}>Нарахування амортизації</Title>

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
            <Button icon={<FilePdfOutlined />} onClick={handleDownloadPdf}>
              Відомість PDF
            </Button>
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
