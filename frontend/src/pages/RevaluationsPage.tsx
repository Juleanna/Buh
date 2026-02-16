import React, { useEffect, useState } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, Select,
  DatePicker, InputNumber, message, Space, Tag,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import type { AssetRevaluation, Asset, PaginatedResponse } from '../types'

const { Title } = Typography

const RevaluationsPage: React.FC = () => {
  const [revaluations, setRevaluations] = useState<AssetRevaluation[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadRevaluations = async (p = page) => {
    setLoading(true)
    const { data } = await api.get<PaginatedResponse<AssetRevaluation>>('/assets/revaluations/', { params: { page: p } })
    setRevaluations(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  useEffect(() => {
    loadRevaluations()
    api.get('/assets/items/', { params: { status: 'active', page_size: 1000 } }).then((res) => {
      setAssets(res.data.results || res.data)
    })
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      await api.post('/assets/revaluations/', {
        ...values,
        date: (values.date as dayjs.Dayjs).format('YYYY-MM-DD'),
      })
      message.success('Переоцінку створено')
      setModalOpen(false)
      form.resetFields()
      loadRevaluations()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка')
    }
  }

  const fmtMoney = (v: string) => Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })

  const columns = [
    {
      title: 'Дата',
      dataIndex: 'date',
      key: 'date',
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'ОЗ', dataIndex: 'asset_name', key: 'asset', ellipsis: true },
    { title: 'Інв.номер', dataIndex: 'asset_inventory_number', key: 'inv' },
    {
      title: 'Тип',
      dataIndex: 'revaluation_type_display',
      key: 'type',
      render: (text: string, record: AssetRevaluation) => (
        <Tag color={record.revaluation_type === 'upward' ? 'green' : 'red'}>{text}</Tag>
      ),
    },
    {
      title: 'Справедлива вартість',
      dataIndex: 'fair_value',
      key: 'fair_value',
      render: fmtMoney,
    },
    {
      title: 'Сума переоцінки',
      dataIndex: 'revaluation_amount',
      key: 'revaluation_amount',
      render: fmtMoney,
    },
    {
      title: 'Зал.вартість до',
      dataIndex: 'old_book_value',
      key: 'old_book_value',
      render: fmtMoney,
    },
    {
      title: 'Зал.вартість після',
      dataIndex: 'new_book_value',
      key: 'new_book_value',
      render: fmtMoney,
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Переоцінки основних засобів</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Нова переоцінка
        </Button>
      </div>

      <Table
        dataSource={revaluations}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 25,
          onChange: (p) => { setPage(p); loadRevaluations(p) },
        }}
        size="small"
      />

      <Modal
        title="Нова переоцінка ОЗ"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="asset" label="Основний засіб" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" placeholder="Оберіть ОЗ"
              options={assets.map(a => ({ value: a.id, label: `${a.inventory_number} — ${a.name}` }))}
            />
          </Form.Item>
          <Space size="large">
            <Form.Item name="date" label="Дата переоцінки" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="document_number" label="Номер документа">
              <Input />
            </Form.Item>
          </Space>
          <Form.Item name="fair_value" label="Справедлива вартість, грн" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default RevaluationsPage
