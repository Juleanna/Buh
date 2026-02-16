import React, { useEffect, useState } from 'react'
import {
  Table, Button, Space, Typography, Tag, Input, Select, Modal,
  Form, InputNumber, DatePicker, message, Tooltip, Popconfirm,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  FilePdfOutlined, SearchOutlined, DownloadOutlined, UploadOutlined, QrcodeOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { downloadPdf } from '../utils/downloadPdf'
import type { Asset, AssetGroup, PaginatedResponse, User } from '../types'

const { Title } = Typography

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disposed: 'red',
  conserved: 'orange',
}

const AssetsPage: React.FC = () => {
  const navigate = useNavigate()
  const [assets, setAssets] = useState<Asset[]>([])
  const [groups, setGroups] = useState<AssetGroup[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form] = Form.useForm()

  const loadAssets = async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<Asset>>('/assets/items/', { params })
    setAssets(data.results)
    setTotal(data.count)
    setLoading(false)
  }

  const loadGroups = async () => {
    const { data } = await api.get('/assets/groups/')
    setGroups(data.results || data)
  }

  const loadUsers = async () => {
    try {
      const { data } = await api.get('/auth/users/')
      setUsers(data.results || data)
    } catch {
      // Може бути недоступно для не-адмінів
    }
  }

  useEffect(() => {
    loadAssets()
    loadGroups()
    loadUsers()
  }, [])

  const handleSubmit = async (values: Record<string, unknown>) => {
    const payload = {
      ...values,
      commissioning_date: (values.commissioning_date as dayjs.Dayjs).format('YYYY-MM-DD'),
      depreciation_start_date: (values.depreciation_start_date as dayjs.Dayjs).format('YYYY-MM-DD'),
    }
    try {
      if (editingId) {
        await api.patch(`/assets/items/${editingId}/`, payload)
        message.success('ОЗ оновлено')
      } else {
        await api.post('/assets/items/', payload)
        message.success('ОЗ створено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      loadAssets()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка збереження')
    }
  }

  const handleEdit = (asset: Asset) => {
    setEditingId(asset.id)
    form.setFieldsValue({
      ...asset,
      commissioning_date: dayjs(asset.commissioning_date),
      depreciation_start_date: dayjs(asset.depreciation_start_date),
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    await api.delete(`/assets/items/${id}/`)
    message.success('ОЗ видалено')
    loadAssets()
  }

  const handleDownloadPdf = (id: number) => {
    downloadPdf(`/documents/asset/${id}/card/`, `asset_card_${id}.pdf`)
  }

  const handleExportExcel = async () => {
    const response = await api.get('/assets/export/excel/', { responseType: 'blob' })
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'assets_export.xlsx'
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const handleImportExcel = async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post('/assets/import/excel/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      message.success(`Імпортовано: ${data.created} ОЗ`)
      if (data.errors?.length) {
        message.warning(`Помилки: ${data.errors.length}`)
      }
      loadAssets()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка імпорту')
    }
  }

  const handleDownloadQR = async (id: number) => {
    const response = await api.get(`/assets/items/${id}/qr/`, { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'image/png' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `qr_${id}.png`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  const columns = [
    { title: 'Інв. номер', dataIndex: 'inventory_number', key: 'inv', width: 120 },
    { title: 'Назва', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: 'Група', dataIndex: 'group_name', key: 'group', width: 150, ellipsis: true },
    {
      title: 'Статус',
      dataIndex: 'status_display',
      key: 'status',
      width: 120,
      render: (text: string, record: Asset) => (
        <Tag color={STATUS_COLORS[record.status]}>{text}</Tag>
      ),
    },
    {
      title: 'Первісна вартість',
      dataIndex: 'initial_cost',
      key: 'initial',
      width: 150,
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
    },
    {
      title: 'Залишкова вартість',
      dataIndex: 'current_book_value',
      key: 'book',
      width: 160,
      render: (v: string) => `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`,
    },
    {
      title: 'Метод',
      dataIndex: 'depreciation_method_display',
      key: 'method',
      width: 140,
      ellipsis: true,
    },
    {
      title: 'Дата введення',
      dataIndex: 'commissioning_date',
      key: 'date',
      width: 120,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 160,
      render: (_: unknown, record: Asset) => (
        <Space size="small">
          <Tooltip title="Переглянути">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/assets/${record.id}`)} />
          </Tooltip>
          <Tooltip title="Редагувати">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Tooltip title="Картка PDF">
            <Button size="small" icon={<FilePdfOutlined />} onClick={() => handleDownloadPdf(record.id)} />
          </Tooltip>
          <Tooltip title="QR-код">
            <Button size="small" icon={<QrcodeOutlined />} onClick={() => handleDownloadQR(record.id)} />
          </Tooltip>
          <Popconfirm title="Видалити ОЗ?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Реєстр основних засобів</Title>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExportExcel}>
            Експорт Excel
          </Button>
          <Button icon={<UploadOutlined />} onClick={() => {
            const input = document.createElement('input')
            input.type = 'file'
            input.accept = '.xlsx,.xls'
            input.onchange = (e) => {
              const file = (e.target as HTMLInputElement).files?.[0]
              if (file) handleImportExcel(file)
            }
            input.click()
          }}>
            Імпорт Excel
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setEditingId(null)
            form.resetFields()
            setModalOpen(true)
          }}>
            Додати ОЗ
          </Button>
        </Space>
      </div>

      <Input.Search
        placeholder="Пошук за назвою або інв. номером..."
        onSearch={(v) => { setSearch(v); setPage(1); loadAssets(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={assets}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadAssets(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        scroll={{ x: 1200 }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати ОЗ' : 'Новий основний засіб'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        width={700}
        okText="Зберегти"
        cancelText="Скасувати"
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="inventory_number" label="Інвентарний номер" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="Назва" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="group" label="Група ОЗ" rules={[{ required: true }]}>
            <Select placeholder="Оберіть групу" showSearch optionFilterProp="label"
              options={groups.map(g => ({ value: g.id, label: `${g.code} — ${g.name}` }))}
            />
          </Form.Item>
          <Space size="large">
            <Form.Item name="initial_cost" label="Первісна вартість, грн" rules={[{ required: true }]}>
              <InputNumber min={0.01} step={0.01} style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="residual_value" label="Ліквідаційна вартість, грн">
              <InputNumber min={0} step={0.01} style={{ width: 200 }} />
            </Form.Item>
          </Space>
          <Space size="large">
            <Form.Item name="depreciation_method" label="Метод амортизації" rules={[{ required: true }]}>
              <Select style={{ width: 300 }} options={[
                { value: 'straight_line', label: 'Прямолінійний' },
                { value: 'reducing_balance', label: 'Зменшення залишкової вартості' },
                { value: 'accelerated_reducing', label: 'Прискореного зменшення' },
                { value: 'cumulative', label: 'Кумулятивний' },
                { value: 'production', label: 'Виробничий' },
              ]} />
            </Form.Item>
            <Form.Item name="useful_life_months" label="Строк використання (міс.)" rules={[{ required: true }]}>
              <InputNumber min={1} style={{ width: 180 }} />
            </Form.Item>
          </Space>
          <Form.Item name="total_production_capacity" label="Загальний обсяг продукції (для виробничого методу)">
            <InputNumber min={0} step={1} style={{ width: 300 }} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="commissioning_date" label="Дата введення в експлуатацію" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="depreciation_start_date" label="Дата початку амортизації" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
          <Form.Item name="responsible_person" label="МВО">
            <Select allowClear placeholder="Оберіть відповідальну особу"
              options={users.map(u => ({ value: u.id, label: u.full_name || u.username }))}
            />
          </Form.Item>
          <Form.Item name="location" label="Місцезнаходження">
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Опис / характеристики">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default AssetsPage
