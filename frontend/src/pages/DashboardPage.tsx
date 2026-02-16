import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Typography, Spin, Progress, Tag, List, Button } from 'antd'
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  StopOutlined,
  DollarOutlined,
  ArrowRightOutlined,
  WarningOutlined,
  PauseCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { Pie } from '@ant-design/charts'
import api from '../api/client'
import type { DashboardData, Notification } from '../types'
import { downloadPdf } from '../utils/downloadPdf'

const { Title, Text } = Typography

const DEPR_METHOD_LABELS: Record<string, string> = {
  straight_line: 'Прямолінійний',
  reducing_balance: 'Зменшення залишкової вартості',
  accelerated_reducing: 'Прискореного зменшення',
  cumulative: 'Кумулятивний',
  production: 'Виробничий',
}

const METHOD_COLORS = ['#1677ff', '#52c41a', '#faad14', '#722ed1', '#13c2c2']
const GROUP_COLORS = ['#1677ff', '#52c41a', '#faad14', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16', '#a0d911', '#2f54eb', '#f5222d']

const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [recentEntries, setRecentEntries] = useState<{ count: number; total_amount: string }>({ count: 0, total_amount: '0' })
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      api.get('/reports/dashboard/'),
      api.get('/assets/notifications/', { params: { page_size: 5 } }).catch(() => ({ data: { results: [] } })),
      api.get('/assets/entries/journal/').catch(() => ({ data: { count: 0, total_amount: '0' } })),
    ]).then(([dashRes, notifRes, entriesRes]) => {
      setData(dashRes.data)
      setNotifications(notifRes.data.results || [])
      setRecentEntries({ count: entriesRes.data.count, total_amount: entriesRes.data.total_amount })
      setLoading(false)
    })
  }, [])

  if (loading || !data) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const totalInitial = Number(data.financials.total_initial_cost)
  const totalDepr = Number(data.financials.total_depreciation)
  const totalBook = Number(data.financials.total_book_value)
  const wearPercent = totalInitial > 0 ? Math.round((totalDepr / totalInitial) * 100) : 0

  const groupColumns = [
    { title: 'Код', dataIndex: 'group__code', key: 'code', width: 60 },
    { title: 'Група', dataIndex: 'group__name', key: 'name' },
    { title: 'К-сть', dataIndex: 'count', key: 'count', width: 80 },
    {
      title: 'Первісна вартість',
      dataIndex: 'total_initial',
      key: 'initial',
      render: (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }) + ' грн',
    },
    {
      title: 'Балансова вартість',
      dataIndex: 'total_book',
      key: 'book',
      render: (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }) + ' грн',
    },
  ]

  const fmtMoney = (v: number) => v.toLocaleString('uk-UA', { minimumFractionDigits: 2 }) + ' грн'

  // Pie chart data for asset groups
  const pieGroupData = data.by_group.map((g) => ({
    type: g.group__name || g.group__code,
    value: g.count,
  }))

  // Pie chart data for depreciation methods
  const pieMethodData = data.depreciation_by_method.map((m) => ({
    type: DEPR_METHOD_LABELS[m.depreciation_method] || m.depreciation_method,
    value: m.count,
  }))

  const pieConfig = {
    height: 280,
    innerRadius: 0.6,
    interaction: { tooltip: {} },
    style: { stroke: '#fff', lineWidth: 2 },
    label: {
      text: 'value',
      style: { fontWeight: 'bold' as const },
    },
    legend: {
      color: {
        title: false,
        position: 'bottom' as const,
        rowPadding: 5,
      },
    },
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Головна панель</Title>
        <Button onClick={() => downloadPdf('/documents/depreciation-report/', 'depreciation-report.pdf')}>
          Завантажити звіт
        </Button>
      </div>

      {/* Stats row */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/assets')}>
            <Statistic
              title="Всього ОЗ"
              value={data.assets.total}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/assets')}>
            <Statistic
              title="В експлуатації"
              value={data.assets.active}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Списано / Консервація"
              value={data.assets.disposed}
              valueStyle={{ color: '#cf1322' }}
              prefix={<StopOutlined />}
              suffix={
                <Text type="secondary" style={{ fontSize: 14 }}>
                  {' '}/ {data.assets.conserved || 0} <PauseCircleOutlined />
                </Text>
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card hoverable onClick={() => navigate('/entries')}>
            <Statistic
              title="Проводок всього"
              value={recentEntries.count}
              prefix={<DollarOutlined />}
              suffix={
                <Text type="secondary" style={{ fontSize: 12 }}>
                  на {fmtMoney(Number(recentEntries.total_amount))}
                </Text>
              }
            />
          </Card>
        </Col>
      </Row>

      {/* Financial summary with wear indicator */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Первісна вартість" value={totalInitial} precision={2} suffix="грн" />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Балансова вартість" value={totalBook} precision={2} suffix="грн" valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">Загальний знос</Text>
            </div>
            <Progress
              percent={wearPercent}
              strokeColor={wearPercent > 80 ? '#ff4d4f' : wearPercent > 50 ? '#faad14' : '#52c41a'}
              format={(p) => `${p}%`}
            />
            <Text>{fmtMoney(totalDepr)}</Text>
            {wearPercent > 80 && (
              <Tag color="red" icon={<WarningOutlined />} style={{ marginLeft: 8 }}>
                Високий знос
              </Tag>
            )}
          </Card>
        </Col>
      </Row>

      {/* Charts row */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="Розподіл ОЗ за групами">
            {pieGroupData.length > 0 ? (
              <Pie
                data={pieGroupData}
                angleField="value"
                colorField="type"
                color={GROUP_COLORS}
                {...pieConfig}
              />
            ) : (
              <Text type="secondary">Немає даних</Text>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="За методами амортизації">
            {pieMethodData.length > 0 ? (
              <Pie
                data={pieMethodData}
                angleField="value"
                colorField="type"
                color={METHOD_COLORS}
                {...pieConfig}
              />
            ) : (
              <Text type="secondary">Немає даних</Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* Table and notifications */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="Основні засоби за групами">
            <Table
              dataSource={data.by_group}
              columns={groupColumns}
              rowKey="group__code"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="За методами амортизації">
            {data.depreciation_by_method.map((item, idx) => {
              const total = data.depreciation_by_method.reduce((s, i) => s + i.count, 0)
              const pct = total > 0 ? Math.round((item.count / total) * 100) : 0
              return (
                <div key={item.depreciation_method} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 13 }}>
                      {DEPR_METHOD_LABELS[item.depreciation_method] || item.depreciation_method}
                    </Text>
                    <Text strong>{item.count}</Text>
                  </div>
                  <Progress
                    percent={pct}
                    showInfo={false}
                    strokeColor={METHOD_COLORS[idx % METHOD_COLORS.length]}
                    size="small"
                  />
                </div>
              )
            })}
          </Card>

          <Card
            title="Останні сповіщення"
            style={{ marginTop: 16 }}
            extra={
              <Button type="link" size="small" onClick={() => navigate('/notifications')}>
                Всі <ArrowRightOutlined />
              </Button>
            }
          >
            {notifications.length === 0 ? (
              <Text type="secondary">Немає сповіщень</Text>
            ) : (
              <List
                size="small"
                dataSource={notifications.slice(0, 5)}
                renderItem={(n) => (
                  <List.Item>
                    <List.Item.Meta
                      title={<Text strong={!n.is_read} style={{ fontSize: 13 }}>{n.title}</Text>}
                      description={<Text type="secondary" style={{ fontSize: 12 }}>{n.notification_type_display}</Text>}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage
