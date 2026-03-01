import React, { useEffect, useState, useMemo, useCallback } from 'react'
import {
  Table, Button, Typography, Modal, Form, Input, DatePicker,
  Space, Popconfirm, InputNumber, Divider,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SearchOutlined,
  SendOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportIconButton } from '../components/ExportButton'
import AsyncSelect from '../components/AsyncSelect'
import type { Asset, AssetTransfer, AssetTransferItem, PaginatedResponse, Location, ResponsiblePerson } from '../types'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title } = Typography

const locationMapOption = (l: Location) => ({
  value: l.id,
  label: l.name,
})

const personMapOption = (p: ResponsiblePerson) => ({
  value: p.id,
  label: `${p.full_name}${p.position_name ? ` (${p.position_name})` : ''}`,
})

const assetMapOption = (a: Asset) => ({
  value: a.id,
  label: `${a.inventory_number} — ${a.name} (${Number(a.current_book_value).toLocaleString('uk-UA')} грн)`,
  bookValue: a.current_book_value,
})

const fmtMoney = (v: string | number) =>
  `${Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 })} грн`

const TransfersPage: React.FC = () => {
  const [transfers, setTransfers] = useState<AssetTransfer[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [items, setItems] = useState<AssetTransferItem[]>([])
  const [form] = Form.useForm()

  const loadTransfers = useCallback(async (p = page, s = search) => {
    setLoading(true)
    const params: Record<string, string | number> = { page: p }
    if (s) params.search = s
    const { data } = await api.get<PaginatedResponse<AssetTransfer>>('/assets/transfers/', { params })
    setTransfers(data.results)
    setTotal(data.count)
    setLoading(false)
  }, [page, search])

  useEffect(() => {
    loadTransfers()
  }, [])

  /* ---- Items management ---- */

  const addItem = () => {
    setItems(prev => [...prev, {
      asset: 0,
      book_value: '0.00',
      quantity: 1,
      notes: '',
    }])
  }

  const removeItem = (index: number) => {
    setItems(prev => prev.filter((_, i) => i !== index))
  }

  const updateItem = (index: number, field: keyof AssetTransferItem, value: unknown) => {
    setItems(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item))
  }

  /* ---- CRUD ---- */

  const handleSubmit = async (values: Record<string, unknown>) => {
    if (items.length === 0 || items.some(it => !it.asset)) {
      message.error('Додайте хоча б один основний засіб')
      return
    }

    try {
      const payload = {
        ...values,
        document_date: (values.document_date as dayjs.Dayjs).format('YYYY-MM-DD'),
        items: items.map(it => ({
          asset: it.asset,
          book_value: it.book_value,
          quantity: it.quantity,
          notes: it.notes || '',
        })),
      }
      if (editingId) {
        await api.put(`/assets/transfers/${editingId}/`, payload)
        message.success('Переміщення оновлено')
      } else {
        await api.post('/assets/transfers/', payload)
        message.success('Переміщення оформлено')
      }
      setModalOpen(false)
      form.resetFields()
      setEditingId(null)
      setItems([])
      loadTransfers()
    } catch (err: any) {
      const detail = err.response?.data
      const msg = typeof detail === 'string' ? detail
        : detail?.detail || detail?.items?.[0]?.asset?.[0] || 'Помилка збереження'
      message.error(msg)
    }
  }

  const handleEdit = async (record: AssetTransfer) => {
    setEditingId(record.id)
    try {
      const { data } = await api.get(`/assets/transfers/${record.id}/`)
      form.setFieldsValue({
        document_number: data.document_number,
        document_date: dayjs(data.document_date),
        from_location: data.from_location,
        to_location: data.to_location,
        from_person: data.from_person,
        to_person: data.to_person,
        reason: data.reason,
        notes: data.notes,
      })
      setItems(
        (data.items || []).map((it: AssetTransferItem) => ({
          id: it.id,
          asset: it.asset,
          asset_name: it.asset_name,
          asset_inventory_number: it.asset_inventory_number,
          book_value: it.book_value,
          quantity: it.quantity,
          notes: it.notes || '',
        })),
      )
      setModalOpen(true)
    } catch {
      message.error('Помилка завантаження переміщення')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/assets/transfers/${id}/`)
      message.success('Переміщення видалено')
      loadTransfers()
    } catch (err: any) {
      message.error(err.response?.data?.detail || 'Помилка видалення')
    }
  }

  /* ---- Table columns ---- */

  const baseColumns = useMemo(() => [
    {
      title: '№ документа',
      dataIndex: 'document_number',
      key: 'doc',
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        (a.document_number || '').localeCompare(b.document_number || ''),
    },
    {
      title: 'Дата',
      dataIndex: 'document_date',
      key: 'date',
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        (a.document_date || '').localeCompare(b.document_date || ''),
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    {
      title: 'Звідки',
      dataIndex: 'from_location_name',
      key: 'from_loc',
      ellipsis: true,
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        (a.from_location_name || '').localeCompare(b.from_location_name || ''),
    },
    {
      title: 'Куди',
      dataIndex: 'to_location_name',
      key: 'to_loc',
      ellipsis: true,
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        (a.to_location_name || '').localeCompare(b.to_location_name || ''),
    },
    {
      title: 'Здав',
      dataIndex: 'from_person_name',
      key: 'from_pers',
      ellipsis: true,
    },
    {
      title: 'Прийняв',
      dataIndex: 'to_person_name',
      key: 'to_pers',
      ellipsis: true,
    },
    {
      title: 'К-сть ОЗ',
      dataIndex: 'items_count',
      key: 'cnt',
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        (a.items_count || 0) - (b.items_count || 0),
    },
    {
      title: 'Сума',
      dataIndex: 'total_value',
      key: 'total',
      sorter: (a: AssetTransfer, b: AssetTransfer) =>
        Number(a.total_value || 0) - Number(b.total_value || 0),
      render: (v: string) => v ? fmtMoney(v) : '—',
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 140,
      render: (_: unknown, record: AssetTransfer) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="Видалити переміщення?" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
          <ExportIconButton
            url={`/documents/transfer/${record.id}/act/`}
            baseFilename={`transfer_act_${record.document_number}`}
            tooltip="Акт переміщення ОЗ-1"
          />
        </Space>
      ),
    },
  ], [])

  const { columns, components } = useResizableColumns(baseColumns)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Переміщення основних засобів</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingId(null)
            form.resetFields()
            setItems([])
            setModalOpen(true)
          }}
        >
          Оформити переміщення
        </Button>
      </div>

      <Input.Search
        placeholder="Пошук за номером документа або підставою..."
        onSearch={(v) => { setSearch(v); setPage(1); loadTransfers(1, v) }}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
        prefix={<SearchOutlined />}
      />

      <Table
        dataSource={transfers}
        columns={columns}
        components={components}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 25,
          onChange: (p) => { setPage(p); loadTransfers(p) },
          showTotal: (t) => `Всього: ${t}`,
        }}
        size="small"
      />

      <Modal
        title={editingId ? 'Редагувати переміщення ОЗ' : 'Переміщення ОЗ'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingId(null); setItems([]) }}
        onOk={() => form.submit()}
        okText={editingId ? 'Зберегти' : 'Оформити'}
        cancelText="Скасувати"
        width={800}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Space size="large" style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
            <Form.Item name="document_number" label="Номер документа" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item name="document_date" label="Дата документа" rules={[{ required: true }]}>
              <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Space size="large" style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
            <Form.Item name="from_location" label="Звідки (місце)">
              <AsyncSelect
                url="/assets/locations/"
                mapOption={locationMapOption}
                placeholder="Оберіть місцезнаходження"
                allowClear
              />
            </Form.Item>
            <Form.Item name="to_location" label="Куди (місце)" rules={[{ required: true }]}>
              <AsyncSelect
                url="/assets/locations/"
                mapOption={locationMapOption}
                placeholder="Оберіть місцезнаходження"
                allowClear
              />
            </Form.Item>
          </Space>

          <Space size="large" style={{ width: '100%' }} styles={{ item: { flex: 1 } }}>
            <Form.Item name="from_person" label="Здав (МВО)">
              <AsyncSelect
                url="/assets/responsible-persons/"
                mapOption={personMapOption}
                placeholder="Оберіть відповідальну особу"
                allowClear
              />
            </Form.Item>
            <Form.Item name="to_person" label="Прийняв (МВО)" rules={[{ required: true }]}>
              <AsyncSelect
                url="/assets/responsible-persons/"
                mapOption={personMapOption}
                placeholder="Оберіть відповідальну особу"
                allowClear
              />
            </Form.Item>
          </Space>

          <Form.Item name="reason" label="Підстава переміщення">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="notes" label="Примітки">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>

        <Divider orientation="left">
          <SendOutlined /> Об&#39;єкти переміщення
        </Divider>

        <Table
          dataSource={items}
          rowKey={(_, i) => String(i)}
          size="small"
          pagination={false}
          footer={() => (
            <Button type="dashed" icon={<PlusOutlined />} onClick={addItem} block>
              Додати ОЗ
            </Button>
          )}
          columns={[
            {
              title: 'Основний засіб',
              key: 'asset',
              width: 320,
              render: (_: unknown, record: AssetTransferItem, index: number) => (
                <AsyncSelect
                  url="/assets/items/"
                  params={{ status: 'active' }}
                  mapOption={assetMapOption}
                  value={record.asset || undefined}
                  onChange={(val: number, opt: any) => {
                    updateItem(index, 'asset', val)
                    if (opt?.bookValue) {
                      updateItem(index, 'book_value', opt.bookValue)
                    }
                  }}
                  placeholder="Пошук ОЗ"
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              title: 'Балансова вартість',
              key: 'book_value',
              width: 160,
              render: (_: unknown, record: AssetTransferItem, index: number) => (
                <InputNumber
                  value={Number(record.book_value)}
                  onChange={(v) => updateItem(index, 'book_value', String(v || 0))}
                  min={0}
                  step={0.01}
                  style={{ width: '100%' }}
                  addonAfter="грн"
                />
              ),
            },
            {
              title: 'К-сть',
              key: 'quantity',
              width: 80,
              render: (_: unknown, record: AssetTransferItem, index: number) => (
                <InputNumber
                  value={record.quantity}
                  onChange={(v) => updateItem(index, 'quantity', v || 1)}
                  min={1}
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              title: 'Примітка',
              key: 'notes',
              render: (_: unknown, record: AssetTransferItem, index: number) => (
                <Input
                  value={record.notes}
                  onChange={(e) => updateItem(index, 'notes', e.target.value)}
                  placeholder="Примітка"
                />
              ),
            },
            {
              title: '',
              key: 'del',
              width: 40,
              render: (_: unknown, __: AssetTransferItem, index: number) => (
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => removeItem(index)} />
              ),
            },
          ]}
        />
      </Modal>
    </div>
  )
}

export default TransfersPage
