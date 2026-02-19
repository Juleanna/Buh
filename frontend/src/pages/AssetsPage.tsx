import React, { useEffect, useState } from 'react'
import {
  Table, Button, Space, Typography, Tag, Input, Select, Modal,
  Form, InputNumber, DatePicker, Tooltip, Popconfirm, Checkbox,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined,
  SearchOutlined, DownloadOutlined, UploadOutlined,
  QrcodeOutlined, PrinterOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportIconButton } from '../components/ExportButton'
import type { Asset, AssetGroup, PaginatedResponse, ResponsiblePerson, Location } from '../types'

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
  const [responsiblePersons, setResponsiblePersons] = useState<ResponsiblePerson[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
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

  const loadResponsiblePersons = async () => {
    try {
      const { data } = await api.get('/assets/responsible-persons/', { params: { is_active: true } })
      setResponsiblePersons(data.results || data)
    } catch { /* */ }
  }

  const loadLocations = async () => {
    try {
      const { data } = await api.get('/assets/locations/', { params: { is_active: true } })
      setLocations(data.results || data)
    } catch { /* */ }
  }

  useEffect(() => {
    loadAssets()
    loadGroups()
    loadResponsiblePersons()
    loadLocations()
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

  const handleEdit = async (asset: Asset) => {
    setEditingId(asset.id)
    try {
      const { data } = await api.get(`/assets/items/${asset.id}/`)
      form.setFieldsValue({
        ...data,
        commissioning_date: dayjs(data.commissioning_date),
        depreciation_start_date: data.depreciation_start_date ? dayjs(data.depreciation_start_date) : null,
      })
    } catch {
      form.setFieldsValue({
        ...asset,
        commissioning_date: dayjs(asset.commissioning_date),
      })
    }
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    await api.delete(`/assets/items/${id}/`)
    message.success('ОЗ видалено')
    loadAssets()
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

  const handlePrint = () => {
    window.print()
  }

  const fmtMoney = (v: string) =>
    `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`

  const columns = [
    {
      title: 'Інв. номер',
      dataIndex: 'inventory_number',
      key: 'inv',
      width: 120,
      sorter: true,
    },
    { title: 'Назва ОЗ', dataIndex: 'name', key: 'name', ellipsis: true },
    { title: 'К-ть', dataIndex: 'quantity', key: 'qty', width: 70 },
    {
      title: 'Сума',
      dataIndex: 'initial_cost',
      key: 'cost',
      width: 150,
      render: (v: string) => fmtMoney(v),
    },
    {
      title: 'Знос',
      dataIndex: 'accumulated_depreciation',
      key: 'depr',
      width: 150,
      render: (v: string) => fmtMoney(v),
    },
    {
      title: 'МВО',
      dataIndex: 'responsible_person_name',
      key: 'mvo',
      width: 180,
      ellipsis: true,
      sorter: true,
    },
    {
      title: 'Статус',
      dataIndex: 'status_display',
      key: 'status',
      width: 110,
      render: (text: string, record: Asset) => (
        <Tag color={STATUS_COLORS[record.status]}>{text}</Tag>
      ),
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: Asset) => (
        <Space size="small">
          <Tooltip title="Переглянути">
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/assets/${record.id}`)} />
          </Tooltip>
          <Tooltip title="Редагувати">
            <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <ExportIconButton
            url={`/documents/asset/${record.id}/card/`}
            baseFilename={`asset_card_${record.id}`}
            tooltip="Картка ОЗ"
          />
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
          <Button icon={<PrinterOutlined />} onClick={handlePrint}>
            Друк
          </Button>
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
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadAssets(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        scroll={{ x: 1100 }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати ОЗ' : 'Новий основний засіб'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null) }}
        onOk={() => form.submit()}
        width={750}
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
            <Form.Item
              name="incoming_depreciation"
              label="Вхідна амортизація, грн"
              tooltip="Знос, нарахований до отримання ОЗ від іншої організації"
              dependencies={['initial_cost']}
              rules={[
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || value <= getFieldValue('initial_cost'))
                      return Promise.resolve()
                    return Promise.reject('Не може перевищувати первісну вартість')
                  },
                }),
              ]}
            >
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
          <Space size="large">
            <Form.Item name="depreciation_rate" label="Норма амортизації (%)">
              <InputNumber min={0} max={100} step={0.01} style={{ width: 180 }}
                placeholder="Річний %"
              />
            </Form.Item>
            <Form.Item name="total_production_capacity" label="Загальний обсяг продукції">
              <InputNumber min={0} step={1} style={{ width: 200 }} />
            </Form.Item>
          </Space>
          <Space size="large">
            <Form.Item name="commissioning_date" label="Дата введення в експлуатацію" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
            <Form.Item name="depreciation_start_date" label="Дата початку амортизації" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
          <Space size="large">
            <Form.Item name="quantity" label="Кількість" initialValue={1}>
              <InputNumber min={1} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="unit_of_measure" label="Одиниця виміру" initialValue="шт.">
              <Input style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="manufacture_year" label="Рік випуску">
              <InputNumber min={1900} max={2100} style={{ width: 120 }} />
            </Form.Item>
          </Space>
          <Space size="large">
            <Form.Item name="factory_number" label="Заводський номер">
              <Input style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="passport_number" label="Номер паспорта">
              <Input style={{ width: 200 }} />
            </Form.Item>
          </Space>
          <Form.Item name="responsible_person" label="МВО">
            <Select allowClear placeholder="Оберіть відповідальну особу" showSearch optionFilterProp="label"
              options={responsiblePersons.map(rp => ({ value: rp.id, label: rp.full_name }))}
            />
          </Form.Item>
          <Form.Item name="location" label="Місцезнаходження">
            <Select allowClear placeholder="Оберіть місцезнаходження" showSearch optionFilterProp="label"
              options={locations.map(loc => ({ value: loc.id, label: loc.name }))}
            />
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
