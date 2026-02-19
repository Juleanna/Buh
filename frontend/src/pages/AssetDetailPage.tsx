import React, { useEffect, useState, useCallback } from 'react'
import {
  Descriptions, Card, Typography, Tag, Button, Space, Table, Spin, Tabs,
  Upload, Image, Popconfirm, Progress, Empty, Modal, Form,
  Input, Select, Row, Col,
} from 'antd'
import { message } from '../utils/globalMessage'
import {
  ArrowLeftOutlined, QrcodeOutlined,
  UploadOutlined, DeleteOutlined, DownloadOutlined,
  FileOutlined, FileImageOutlined, EyeOutlined,
  InboxOutlined, FileTextOutlined, CameraOutlined, FilePdfOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import api from '../api/client'
import { ExportDropdownButton } from '../components/ExportButton'
import type {
  Asset, DepreciationRecord, AssetAttachment,
  AssetRevaluation, AssetImprovement, AccountEntry,
} from '../types'

const { Title, Text } = Typography

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  disposed: 'red',
  conserved: 'orange',
}

const FILE_TYPE_ICONS: Record<string, React.ReactNode> = {
  scan: <FileTextOutlined />,
  photo: <CameraOutlined />,
  act: <FilePdfOutlined />,
  invoice: <FileOutlined />,
  other: <FileOutlined />,
}

const FILE_TYPE_OPTIONS = [
  { value: 'scan', label: 'Скан документа' },
  { value: 'photo', label: 'Фотографія' },
  { value: 'act', label: 'Акт' },
  { value: 'invoice', label: 'Накладна' },
  { value: 'other', label: 'Інше' },
]

const isImageFile = (name: string) => /\.(jpg|jpeg|png|gif|bmp|webp|tiff?)$/i.test(name)

const AssetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [asset, setAsset] = useState<Asset | null>(null)
  const [deprRecords, setDeprRecords] = useState<DepreciationRecord[]>([])
  const [attachments, setAttachments] = useState<AssetAttachment[]>([])
  const [revaluations, setRevaluations] = useState<AssetRevaluation[]>([])
  const [improvements, setImprovement] = useState<AssetImprovement[]>([])
  const [entries, setEntries] = useState<AccountEntry[]>([])
  const [qrUrl, setQrUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadForm] = Form.useForm()
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const loadAttachments = useCallback(async () => {
    try {
      const { data } = await api.get('/assets/attachments/', { params: { asset: id } })
      setAttachments(data.results || data)
    } catch { /* ignore */ }
  }, [id])

  useEffect(() => {
    Promise.all([
      api.get(`/assets/items/${id}/`),
      api.get('/assets/depreciation/', { params: { asset: id } }),
      api.get('/assets/attachments/', { params: { asset: id } }).catch(() => ({ data: { results: [] } })),
      api.get('/assets/revaluations/', { params: { asset: id } }).catch(() => ({ data: { results: [] } })),
      api.get('/assets/improvements/', { params: { asset: id } }).catch(() => ({ data: { results: [] } })),
      api.get('/assets/entries/', { params: { asset: id } }).catch(() => ({ data: { results: [] } })),
    ]).then(([assetRes, deprRes, attachRes, revalRes, imprRes, entriesRes]) => {
      setAsset(assetRes.data)
      setDeprRecords(deprRes.data.results || deprRes.data)
      setAttachments(attachRes.data.results || attachRes.data)
      setRevaluations(revalRes.data.results || revalRes.data)
      setImprovement(imprRes.data.results || imprRes.data)
      setEntries(entriesRes.data.results || entriesRes.data)
      setLoading(false)
    })
  }, [id])

  // Load QR code as blob URL
  useEffect(() => {
    if (!id) return
    api.get(`/assets/items/${id}/qr/`, { responseType: 'blob' })
      .then((res) => {
        const blob = new Blob([res.data], { type: 'image/png' })
        setQrUrl(URL.createObjectURL(blob))
      })
      .catch(() => { /* QR not available */ })
    return () => {
      if (qrUrl) URL.revokeObjectURL(qrUrl)
    }
  }, [id])

  if (loading || !asset) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  const wearPercent = Number(asset.initial_cost) > 0
    ? Number(((Number(asset.accumulated_depreciation) / Number(asset.initial_cost)) * 100).toFixed(1))
    : 0

  const fmtMoney = (v: string | number) =>
    Number(v).toLocaleString('uk-UA', { minimumFractionDigits: 2 }) + ' грн'

  const handleDownloadQR = () => {
    if (!qrUrl) return
    const link = document.createElement('a')
    link.href = qrUrl
    link.download = `qr_${asset.inventory_number}.png`
    link.click()
  }

  const handleUploadSubmit = async (values: Record<string, string>) => {
    if (!uploadFile) {
      message.error('Оберіть файл')
      return
    }
    setUploading(true)
    const formData = new FormData()
    formData.append('file', uploadFile)
    formData.append('asset', String(id))
    formData.append('name', values.name || uploadFile.name)
    formData.append('file_type', values.file_type || 'other')
    if (values.description) formData.append('description', values.description)
    try {
      await api.post('/assets/attachments/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      message.success('Файл завантажено')
      setUploadModalOpen(false)
      setUploadFile(null)
      uploadForm.resetFields()
      loadAttachments()
    } catch {
      message.error('Помилка завантаження файлу')
    } finally {
      setUploading(false)
    }
  }

  const openUploadModal = () => {
    setUploadFile(null)
    uploadForm.resetFields()
    setUploadModalOpen(true)
  }

  const handlePreview = (attach: AssetAttachment) => {
    // For images, show preview; for others, open in new tab
    if (isImageFile(attach.name || attach.file)) {
      setPreviewImage(attach.file)
    } else {
      window.open(attach.file, '_blank')
    }
  }

  const handleDeleteAttachment = async (attachId: number) => {
    try {
      await api.delete(`/assets/attachments/${attachId}/`)
      message.success('Файл видалено')
      loadAttachments()
    } catch {
      message.error('Помилка видалення')
    }
  }

  const handleDownloadAttachment = async (attach: AssetAttachment) => {
    try {
      const response = await api.get(attach.file, { responseType: 'blob', baseURL: '' })
      const blob = new Blob([response.data])
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = attach.name || 'file'
      link.click()
      URL.revokeObjectURL(link.href)
    } catch {
      // Try opening in a new tab if download fails
      window.open(attach.file, '_blank')
    }
  }

  const deprColumns = [
    {
      title: 'Період',
      key: 'period',
      render: (_: unknown, r: DepreciationRecord) => `${String(r.period_month).padStart(2, '0')}.${r.period_year}`,
    },
    {
      title: 'Сума, грн',
      dataIndex: 'amount',
      render: (v: string) => fmtMoney(v),
    },
    {
      title: 'Залишкова до',
      dataIndex: 'book_value_before',
      render: (v: string) => fmtMoney(v),
    },
    {
      title: 'Залишкова після',
      dataIndex: 'book_value_after',
      render: (v: string) => fmtMoney(v),
    },
    { title: 'Метод', dataIndex: 'method_display' },
  ]

  const revalColumns = [
    {
      title: 'Дата', dataIndex: 'date', width: 110,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    {
      title: 'Тип', dataIndex: 'revaluation_type_display', width: 120,
      render: (text: string, r: AssetRevaluation) => (
        <Tag color={r.revaluation_type === 'upward' ? 'green' : 'red'}>{text}</Tag>
      ),
    },
    { title: 'Документ', dataIndex: 'document_number', width: 140 },
    { title: 'Справедлива вартість', dataIndex: 'fair_value', render: (v: string) => fmtMoney(v) },
    { title: 'Зал. до', dataIndex: 'old_book_value', render: (v: string) => fmtMoney(v) },
    { title: 'Зал. після', dataIndex: 'new_book_value', render: (v: string) => fmtMoney(v) },
    { title: 'Сума переоцінки', dataIndex: 'revaluation_amount', render: (v: string) => fmtMoney(v) },
  ]

  const imprColumns = [
    {
      title: 'Дата', dataIndex: 'date', width: 110,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'Тип', dataIndex: 'improvement_type_display', width: 150 },
    { title: 'Опис', dataIndex: 'description', ellipsis: true },
    { title: 'Сума, грн', dataIndex: 'amount', width: 130, render: (v: string) => fmtMoney(v) },
    { title: 'Виконавець', dataIndex: 'contractor', width: 150, ellipsis: true },
    {
      title: 'Збільшує вартість', dataIndex: 'increases_value', width: 130,
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? 'Так' : 'Ні'}</Tag>,
    },
  ]

  const entryColumns = [
    {
      title: 'Дата', dataIndex: 'date', width: 110,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY'),
    },
    { title: 'Тип', dataIndex: 'entry_type_display', width: 200, ellipsis: true },
    { title: 'Дт', dataIndex: 'debit_account', width: 80 },
    { title: 'Кт', dataIndex: 'credit_account', width: 80 },
    { title: 'Сума, грн', dataIndex: 'amount', width: 130, render: (v: string) => fmtMoney(v) },
    { title: 'Опис', dataIndex: 'description', ellipsis: true },
  ]

  const attachColumns = [
    {
      title: '', dataIndex: 'file', width: 60,
      render: (url: string, record: AssetAttachment) => {
        if (isImageFile(record.name || url)) {
          return (
            <Image
              src={url}
              alt={record.name}
              width={40}
              height={40}
              style={{ objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }}
              preview={false}
              onClick={() => setPreviewImage(url)}
            />
          )
        }
        return <span style={{ fontSize: 24 }}>{FILE_TYPE_ICONS[record.file_type] || <FileOutlined />}</span>
      },
    },
    { title: 'Назва', dataIndex: 'name', ellipsis: true },
    { title: 'Тип', dataIndex: 'file_type_display', width: 120 },
    { title: 'Опис', dataIndex: 'description', width: 150, ellipsis: true },
    {
      title: 'Розмір', dataIndex: 'file_size', width: 100,
      render: (v: number) => {
        if (!v) return '—'
        if (v < 1024) return `${v} Б`
        if (v < 1048576) return `${(v / 1024).toFixed(1)} КБ`
        return `${(v / 1048576).toFixed(1)} МБ`
      },
    },
    { title: 'Завантажив', dataIndex: 'uploaded_by_name', width: 140 },
    {
      title: 'Дата', dataIndex: 'uploaded_at', width: 120,
      render: (d: string) => dayjs(d).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Дії', key: 'actions', width: 120,
      render: (_: unknown, record: AssetAttachment) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => handlePreview(record)} title="Переглянути" />
          <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownloadAttachment(record)} title="Завантажити" />
          <Popconfirm title="Видалити файл?" onConfirm={() => handleDeleteAttachment(record.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger title="Видалити" />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/assets')}>
          До реєстру
        </Button>
        <ExportDropdownButton
          url={`/documents/asset/${id}/card/`}
          baseFilename={`asset_card_${id}`}
          label="Картка ОЗ"
        />
        <Button icon={<QrcodeOutlined />} onClick={handleDownloadQR} disabled={!qrUrl}>
          Завантажити QR-код
        </Button>
      </Space>

      <Title level={4}>{asset.inventory_number} — {asset.name}</Title>

      <Tabs items={[
        {
          key: 'info',
          label: 'Загальна інформація',
          children: (
            <Card>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Інвентарний номер">{asset.inventory_number}</Descriptions.Item>
                <Descriptions.Item label="Статус">
                  <Tag color={STATUS_COLORS[asset.status]}>{asset.status_display}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Група ОЗ">{asset.group_name}</Descriptions.Item>
                <Descriptions.Item label="Метод амортизації">{asset.depreciation_method_display}</Descriptions.Item>
                <Descriptions.Item label="Первісна вартість">{fmtMoney(asset.initial_cost)}</Descriptions.Item>
                <Descriptions.Item label="Ліквідаційна вартість">{fmtMoney(asset.residual_value)}</Descriptions.Item>
                <Descriptions.Item label="Вхідна амортизація">
                  {Number(asset.incoming_depreciation) > 0 ? fmtMoney(asset.incoming_depreciation) : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="Залишкова вартість">
                  <Text strong style={{ color: '#1677ff' }}>{fmtMoney(asset.current_book_value)}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Накопичений знос">
                  <Space>
                    <span>{fmtMoney(asset.accumulated_depreciation)}</span>
                    <Progress
                      percent={wearPercent}
                      size="small"
                      style={{ width: 100 }}
                      strokeColor={wearPercent > 80 ? '#ff4d4f' : wearPercent > 50 ? '#faad14' : '#52c41a'}
                    />
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="Строк використання">{asset.useful_life_months} міс.</Descriptions.Item>
                <Descriptions.Item label="Норма амортизації">{asset.depreciation_rate ? `${asset.depreciation_rate}%` : '—'}</Descriptions.Item>
                <Descriptions.Item label="Дата введення">
                  {dayjs(asset.commissioning_date).format('DD.MM.YYYY')}
                </Descriptions.Item>
                <Descriptions.Item label="Рік випуску">{asset.manufacture_year || '—'}</Descriptions.Item>
                <Descriptions.Item label="МВО">{asset.responsible_person_name || '—'}</Descriptions.Item>
                <Descriptions.Item label="Місцезнаходження">{asset.location_name || '—'}</Descriptions.Item>
                <Descriptions.Item label="Кількість">{asset.quantity} {asset.unit_of_measure}</Descriptions.Item>
                <Descriptions.Item label="Заводський номер">{asset.factory_number || '—'}</Descriptions.Item>
                <Descriptions.Item label="Номер паспорта" span={2}>{asset.passport_number || '—'}</Descriptions.Item>
                <Descriptions.Item label="Опис" span={2}>{asset.description || '—'}</Descriptions.Item>
              </Descriptions>

              {/* QR Code inline */}
              {qrUrl && (
                <Card
                  title="QR-код"
                  size="small"
                  style={{ marginTop: 16, maxWidth: 300 }}
                  extra={<Button size="small" icon={<DownloadOutlined />} onClick={handleDownloadQR}>Завантажити</Button>}
                >
                  <div style={{ textAlign: 'center' }}>
                    <Image src={qrUrl} alt="QR Code" width={200} preview={false} />
                  </div>
                </Card>
              )}
            </Card>
          ),
        },
        {
          key: 'depreciation',
          label: `Амортизація (${deprRecords.length})`,
          children: (
            <Table
              dataSource={deprRecords}
              columns={deprColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 12 }}
            />
          ),
        },
        {
          key: 'attachments',
          label: `Документи (${attachments.length})`,
          children: (
            <div>
              <div style={{ marginBottom: 16 }}>
                <Button icon={<UploadOutlined />} type="primary" onClick={openUploadModal}>
                  Прикріпити документ
                </Button>
              </div>

              {/* Image gallery for photos/scans */}
              {attachments.filter(a => isImageFile(a.name || a.file)).length > 0 && (
                <Card title="Скани та фотографії" size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={[12, 12]}>
                    {attachments.filter(a => isImageFile(a.name || a.file)).map(a => (
                      <Col key={a.id}>
                        <Card
                          hoverable
                          size="small"
                          style={{ width: 140 }}
                          cover={
                            <Image
                              src={a.file}
                              alt={a.name}
                              height={100}
                              style={{ objectFit: 'cover' }}
                              preview={{ mask: 'Переглянути' }}
                            />
                          }
                        >
                          <Card.Meta
                            title={<Text ellipsis style={{ fontSize: 12 }}>{a.name}</Text>}
                            description={<Text type="secondary" style={{ fontSize: 11 }}>{a.file_type_display}</Text>}
                          />
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </Card>
              )}

              {attachments.length > 0 ? (
                <Table
                  dataSource={attachments}
                  columns={attachColumns}
                  rowKey="id"
                  size="small"
                  pagination={false}
                />
              ) : (
                <Empty description="Немає прикріплених документів" />
              )}

              {/* Upload modal */}
              <Modal
                title="Прикріпити документ"
                open={uploadModalOpen}
                onCancel={() => { setUploadModalOpen(false); setUploadFile(null) }}
                onOk={() => uploadForm.submit()}
                confirmLoading={uploading}
                okText="Завантажити"
                cancelText="Скасувати"
                width={500}
              >
                <Form form={uploadForm} layout="vertical" onFinish={handleUploadSubmit}>
                  <Form.Item label="Файл" required>
                    <Upload.Dragger
                      beforeUpload={(file) => {
                        setUploadFile(file as File)
                        uploadForm.setFieldsValue({ name: file.name })
                        // Auto-detect type
                        if (isImageFile(file.name)) {
                          const ext = file.name.toLowerCase()
                          uploadForm.setFieldsValue({
                            file_type: ext.match(/\.(jpg|jpeg|png|gif|bmp|webp)$/i) ? 'photo' : 'scan',
                          })
                        } else if (file.name.toLowerCase().endsWith('.pdf')) {
                          uploadForm.setFieldsValue({ file_type: 'scan' })
                        }
                        return false
                      }}
                      maxCount={1}
                      fileList={uploadFile ? [{ uid: '-1', name: uploadFile.name, status: 'done' as const }] : []}
                      onRemove={() => setUploadFile(null)}
                    >
                      <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                      <p className="ant-upload-text">Перетягніть файл сюди або натисніть для вибору</p>
                      <p className="ant-upload-hint">Скани, фото, акти, накладні</p>
                    </Upload.Dragger>
                  </Form.Item>
                  <Form.Item name="file_type" label="Тип документа" rules={[{ required: true, message: 'Оберіть тип' }]} initialValue="scan">
                    <Select options={FILE_TYPE_OPTIONS} />
                  </Form.Item>
                  <Form.Item name="name" label="Назва">
                    <Input placeholder="Назва файлу" />
                  </Form.Item>
                  <Form.Item name="description" label="Опис">
                    <Input.TextArea rows={2} placeholder="Короткий опис документа..." />
                  </Form.Item>
                </Form>
              </Modal>

              {/* Image preview modal */}
              {previewImage && (
                <Image
                  style={{ display: 'none' }}
                  src={previewImage}
                  preview={{
                    visible: true,
                    onVisibleChange: (vis) => { if (!vis) setPreviewImage(null) },
                  }}
                />
              )}
            </div>
          ),
        },
        {
          key: 'revaluations',
          label: `Переоцінки (${revaluations.length})`,
          children: revaluations.length > 0 ? (
            <Table
              dataSource={revaluations}
              columns={revalColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          ) : (
            <Empty description="Немає переоцінок" />
          ),
        },
        {
          key: 'improvements',
          label: `Поліпшення (${improvements.length})`,
          children: improvements.length > 0 ? (
            <Table
              dataSource={improvements}
              columns={imprColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          ) : (
            <Empty description="Немає поліпшень" />
          ),
        },
        {
          key: 'entries',
          label: `Проводки (${entries.length})`,
          children: entries.length > 0 ? (
            <Table
              dataSource={entries}
              columns={entryColumns}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 20 }}
            />
          ) : (
            <Empty description="Немає проводок" />
          ),
        },
      ]} />
    </div>
  )
}

export default AssetDetailPage
