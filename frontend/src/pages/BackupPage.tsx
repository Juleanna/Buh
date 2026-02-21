import React, { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Card, Row, Col, Button, Typography, Statistic, Space, Alert, Spin,
  Table, Tag, Divider, Collapse, TimePicker, Switch, Upload,
} from 'antd'
import { message, modal } from '../utils/globalMessage'
import {
  DatabaseOutlined,
  DownloadOutlined,
  CloudServerOutlined,
  TableOutlined,
  HddOutlined,
  FileTextOutlined,
  CodeOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  UndoOutlined,
  UploadOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import api from '../api/client'
import { useResizableColumns } from '../hooks/useResizableColumns'

const { Title, Text, Paragraph } = Typography

interface DbInfo {
  database_name: string
  database_host: string
  database_size: string
  tables_count: number
  assets_count: number
}

interface BackupSchedule {
  enabled: boolean
  hour: number
  minute: number
}

interface GDriveStatus {
  is_configured: boolean
  has_credentials: boolean
  has_token: boolean
  folder_id: string
  retention_days: number
  last_backup: BackupRecord | null
  schedule: BackupSchedule
}

interface BackupRecord {
  id: number
  filename: string
  file_size: number
  file_size_display: string
  status: string
  status_display: string
  gdrive_file_id: string
  gdrive_link: string
  error_message: string
  is_auto: boolean
  created_at: string
}

interface BackupHistoryItem {
  filename: string
  format: string
  timestamp: string
}

const BackupPage: React.FC = () => {
  const [dbInfo, setDbInfo] = useState<DbInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloadingSql, setDownloadingSql] = useState(false)
  const [downloadingJson, setDownloadingJson] = useState(false)
  const [history, setHistory] = useState<BackupHistoryItem[]>([])

  // Google Drive state
  const [gdriveStatus, setGdriveStatus] = useState<GDriveStatus | null>(null)
  const [gdriveLoading, setGdriveLoading] = useState(true)
  const [cloudBackupLoading, setCloudBackupLoading] = useState(false)
  const [backupRecords, setBackupRecords] = useState<BackupRecord[]>([])
  const [backupRecordsTotal, setBackupRecordsTotal] = useState(0)
  const [backupPage, setBackupPage] = useState(1)
  const [backupRecordsLoading, setBackupRecordsLoading] = useState(false)
  const [authLoading, setAuthLoading] = useState(false)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [restoreLoading, setRestoreLoading] = useState(false)

  // Перевірити query параметри після OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const authResult = params.get('gdrive_auth')
    if (authResult === 'success') {
      message.success('Google Drive успішно авторизовано!')
      window.history.replaceState({}, '', '/backup')
    } else if (authResult === 'error') {
      message.error('Помилка авторизації Google Drive: ' + (params.get('message') || ''))
      window.history.replaceState({}, '', '/backup')
    }
  }, [])

  useEffect(() => {
    api.get('/reports/backup/')
      .then((res) => {
        setDbInfo(res.data)
        setLoading(false)
      })
      .catch(() => {
        message.error('Не вдалося отримати інформацію про БД')
        setLoading(false)
      })
  }, [])

  const loadGdriveStatus = useCallback(() => {
    setGdriveLoading(true)
    api.get('/reports/backup/gdrive-status/')
      .then((res) => {
        setGdriveStatus(res.data)
        setGdriveLoading(false)
      })
      .catch(() => {
        setGdriveLoading(false)
      })
  }, [])

  const loadBackupRecords = useCallback((page = 1) => {
    setBackupRecordsLoading(true)
    api.get('/reports/backup/history/', { params: { page } })
      .then((res) => {
        setBackupRecords(res.data.results)
        setBackupRecordsTotal(res.data.count)
        setBackupRecordsLoading(false)
      })
      .catch(() => {
        setBackupRecordsLoading(false)
      })
  }, [])

  useEffect(() => {
    loadGdriveStatus()
    loadBackupRecords()
  }, [loadGdriveStatus, loadBackupRecords])

  const handleDownload = async (format: 'sql' | 'json') => {
    const isSql = format === 'sql'
    isSql ? setDownloadingSql(true) : setDownloadingJson(true)

    try {
      const response = await api.post('/reports/backup/', { format }, {
        responseType: 'blob',
      })

      const filename = response.headers['x-backup-filename']
        || `backup_${format === 'sql' ? 'database' : 'data'}_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.${format}`

      const blob = new Blob([response.data], {
        type: format === 'sql' ? 'application/sql' : 'application/json',
      })
      const link = document.createElement('a')
      link.href = URL.createObjectURL(blob)
      link.download = filename
      link.click()
      URL.revokeObjectURL(link.href)

      setHistory((prev) => [
        {
          filename,
          format: format.toUpperCase(),
          timestamp: new Date().toLocaleString('uk-UA'),
        },
        ...prev,
      ])

      message.success(`Бекап ${format.toUpperCase()} успішно завантажено`)
    } catch (err: any) {
      if (err.response?.data instanceof Blob) {
        const text = await err.response.data.text()
        try {
          const parsed = JSON.parse(text)
          message.error(parsed.error || 'Помилка створення бекапу')
        } catch {
          message.error('Помилка створення бекапу')
        }
      } else {
        message.error('Помилка створення бекапу')
      }
    } finally {
      isSql ? setDownloadingSql(false) : setDownloadingJson(false)
    }
  }

  const handleGdriveAuth = async () => {
    setAuthLoading(true)
    try {
      const res = await api.get('/reports/backup/gdrive-auth/')
      window.location.href = res.data.auth_url
    } catch (err: any) {
      message.error(err.response?.data?.error || 'Помилка авторизації')
      setAuthLoading(false)
    }
  }

  const handleCloudBackup = async () => {
    setCloudBackupLoading(true)
    try {
      const res = await api.post('/reports/backup/cloud/')
      message.success(res.data.message || 'Бекап успішно створено!')
      loadBackupRecords(1)
      loadGdriveStatus()
    } catch (err: any) {
      message.error(err.response?.data?.error || 'Помилка створення бекапу')
    } finally {
      setCloudBackupLoading(false)
    }
  }

  const handleScheduleChange = async (enabled: boolean, hour?: number, minute?: number) => {
    const schedule = gdriveStatus?.schedule
    const newHour = hour ?? schedule?.hour ?? 2
    const newMinute = minute ?? schedule?.minute ?? 0
    setScheduleLoading(true)
    try {
      const res = await api.put('/reports/backup/schedule/', {
        enabled,
        hour: newHour,
        minute: newMinute,
      })
      message.success(res.data.message || 'Розклад оновлено')
      loadGdriveStatus()
    } catch (err: any) {
      message.error(err.response?.data?.error || 'Помилка оновлення розкладу')
    } finally {
      setScheduleLoading(false)
    }
  }

  const handleCloudRestore = (record: BackupRecord) => {
    modal.confirm({
      title: 'Відновлення з хмарного бекапу',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <Paragraph type="danger" style={{ marginBottom: 8 }}>
            <strong>Поточні дані будуть замінені!</strong>
          </Paragraph>
          <Paragraph>
            Бекап: <Text strong>{record.filename}</Text>
            <br />
            Дата: <Text strong>{dayjs(record.created_at).format('DD.MM.YYYY HH:mm')}</Text>
            <br />
            Розмір: <Text strong>{record.file_size_display}</Text>
          </Paragraph>
          <Alert
            message="Рекомендуємо спочатку створити бекап поточного стану перед відновленням."
            type="warning"
            showIcon
            style={{ marginTop: 8 }}
          />
        </div>
      ),
      okText: 'Відновити',
      okType: 'danger',
      cancelText: 'Скасувати',
      width: 480,
      onOk: async () => {
        setRestoreLoading(true)
        try {
          const res = await api.post('/reports/backup/restore-cloud/', { record_id: record.id })
          message.success(res.data.message || 'Дані успішно відновлено!')
          // Перезавантажити інформацію про БД
          api.get('/reports/backup/').then((r) => setDbInfo(r.data))
        } catch (err: any) {
          message.error(err.response?.data?.error || 'Помилка відновлення з хмарного бекапу')
        } finally {
          setRestoreLoading(false)
        }
      },
    })
  }

  const handleFileRestore = (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (!['sql', 'json'].includes(ext || '')) {
      message.error('Підтримуються тільки файли .sql та .json')
      return
    }

    modal.confirm({
      title: 'Відновлення з локального файлу',
      icon: <ExclamationCircleOutlined />,
      content: (
        <div>
          <Paragraph type="danger" style={{ marginBottom: 8 }}>
            <strong>Поточні дані будуть замінені!</strong>
          </Paragraph>
          <Paragraph>
            Файл: <Text strong>{file.name}</Text>
            <br />
            Формат: <Text strong>{ext?.toUpperCase()}</Text>
            <br />
            Розмір: <Text strong>{(file.size / 1024).toFixed(1)} KB</Text>
          </Paragraph>
          <Alert
            message="Рекомендуємо спочатку створити бекап поточного стану перед відновленням."
            type="warning"
            showIcon
            style={{ marginTop: 8 }}
          />
        </div>
      ),
      okText: 'Відновити',
      okType: 'danger',
      cancelText: 'Скасувати',
      width: 480,
      onOk: async () => {
        setRestoreLoading(true)
        try {
          const formData = new FormData()
          formData.append('file', file)
          const res = await api.post('/reports/backup/restore/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 600000,
          })
          message.success(res.data.message || 'Дані успішно відновлено!')
          api.get('/reports/backup/').then((r) => setDbInfo(r.data))
        } catch (err: any) {
          message.error(err.response?.data?.error || 'Помилка відновлення з файлу')
        } finally {
          setRestoreLoading(false)
        }
      },
    })
  }

  const statusColor = (status: string) => {
    switch (status) {
      case 'success': return 'green'
      case 'failed': return 'red'
      case 'pending': return 'blue'
      default: return 'default'
    }
  }

  const statusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircleOutlined />
      case 'failed': return <CloseCircleOutlined />
      case 'pending': return <SyncOutlined spin />
      default: return null
    }
  }

  const baseCloudColumns = useMemo(() => [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
      sorter: (a: BackupRecord, b: BackupRecord) => a.created_at.localeCompare(b.created_at),
    },
    {
      title: 'Файл',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
      sorter: (a: BackupRecord, b: BackupRecord) => a.filename.localeCompare(b.filename),
    },
    {
      title: 'Розмір',
      dataIndex: 'file_size_display',
      key: 'file_size_display',
      width: 100,
      sorter: (a: BackupRecord, b: BackupRecord) => a.file_size - b.file_size,
    },
    {
      title: 'Тип',
      dataIndex: 'is_auto',
      key: 'is_auto',
      width: 100,
      sorter: (a: BackupRecord, b: BackupRecord) => Number(a.is_auto) - Number(b.is_auto),
      render: (v: boolean) => (
        <Tag color={v ? 'purple' : 'cyan'} icon={v ? <ClockCircleOutlined /> : undefined}>
          {v ? 'Авто' : 'Ручний'}
        </Tag>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      sorter: (a: BackupRecord, b: BackupRecord) => a.status.localeCompare(b.status),
      render: (status: string, record: BackupRecord) => (
        <Tag color={statusColor(status)} icon={statusIcon(status)}>
          {record.status_display}
        </Tag>
      ),
    },
    {
      title: 'Посилання',
      key: 'link',
      width: 100,
      render: (_: unknown, record: BackupRecord) => record.gdrive_link ? (
        <a href={record.gdrive_link} target="_blank" rel="noopener noreferrer">
          <LinkOutlined /> Відкрити
        </a>
      ) : record.error_message ? (
        <Text type="danger" style={{ fontSize: 12 }}>{record.error_message.slice(0, 50)}</Text>
      ) : '—',
    },
    {
      title: 'Дії',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: BackupRecord) => record.status === 'success' ? (
        <Button
          size="small"
          icon={<UndoOutlined />}
          onClick={() => handleCloudRestore(record)}
          loading={restoreLoading}
        >
          Відновити
        </Button>
      ) : null,
    },
  ], [restoreLoading])

  const { columns: cloudColumns, components: cloudComponents } = useResizableColumns(baseCloudColumns)

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>Резервне копіювання</Title>

      {/* Google Drive Section */}
      <Card
        title={
          <Space>
            <CloudUploadOutlined />
            <span>Google Drive — хмарний бекап</span>
            {gdriveStatus && (
              <Tag
                color={gdriveStatus.is_configured ? 'green' : 'orange'}
                icon={gdriveStatus.is_configured ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              >
                {gdriveStatus.is_configured ? 'Підключено' : 'Не налаштовано'}
              </Tag>
            )}
          </Space>
        }
        style={{ marginBottom: 24 }}
        loading={gdriveLoading}
      >
        {gdriveStatus?.is_configured ? (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Останній бекап"
                  value={gdriveStatus.last_backup
                    ? dayjs(gdriveStatus.last_backup.created_at).format('DD.MM.YYYY HH:mm')
                    : 'Немає'
                  }
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Розмір останнього"
                  value={gdriveStatus.last_backup?.file_size_display || '—'}
                  prefix={<HddOutlined />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic
                  title="Зберігання"
                  value={`${gdriveStatus.retention_days} днів`}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
            </Row>

            <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }}>
              <Row align="middle" gutter={[16, 12]}>
                <Col>
                  <Space>
                    <Text strong>Автобекап:</Text>
                    <Switch
                      checked={gdriveStatus.schedule?.enabled ?? false}
                      onChange={(checked) => handleScheduleChange(checked)}
                      loading={scheduleLoading}
                    />
                    <Text type={gdriveStatus.schedule?.enabled ? 'success' : 'secondary'}>
                      {gdriveStatus.schedule?.enabled ? 'Увімкнено' : 'Вимкнено'}
                    </Text>
                  </Space>
                </Col>
                <Col>
                  <Space>
                    <Text>Час:</Text>
                    <TimePicker
                      value={dayjs().hour(gdriveStatus.schedule?.hour ?? 2).minute(gdriveStatus.schedule?.minute ?? 0)}
                      format="HH:mm"
                      onChange={(time) => {
                        if (time) {
                          handleScheduleChange(
                            gdriveStatus.schedule?.enabled ?? false,
                            time.hour(),
                            time.minute(),
                          )
                        }
                      }}
                      disabled={scheduleLoading}
                      allowClear={false}
                      style={{ width: 90 }}
                    />
                    <Text type="secondary">щодня</Text>
                  </Space>
                </Col>
              </Row>
              <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
                Бекап включає: базу даних (pg_dump), медіафайли та .env конфігурацію.
              </Text>
            </Card>

            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              onClick={handleCloudBackup}
              loading={cloudBackupLoading}
              size="large"
            >
              Створити бекап зараз
            </Button>
          </>
        ) : (
          <>
            {gdriveStatus?.has_credentials && !gdriveStatus?.has_token ? (
              <Alert
                message="Потрібна авторизація Google Drive"
                description="Credentials файл знайдено. Натисніть кнопку нижче, щоб увійти в Google акаунт і дозволити доступ до Drive."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            ) : (
              <Alert
                message="Google Drive не налаштовано"
                description="Для увімкнення хмарних бекапів потрібно налаштувати OAuth2 авторизацію Google. Дивіться інструкцію нижче."
                type="warning"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {gdriveStatus?.has_credentials && !gdriveStatus?.has_token && (
              <Button
                type="primary"
                icon={<CloudUploadOutlined />}
                onClick={handleGdriveAuth}
                loading={authLoading}
                size="large"
                style={{ marginBottom: 16 }}
              >
                Авторизувати Google Drive
              </Button>
            )}

            <Collapse
              items={[{
                key: '1',
                label: <><InfoCircleOutlined /> Інструкція з налаштування Google Drive</>,
                children: (
                  <ol style={{ paddingLeft: 20, lineHeight: 2 }}>
                    <li>Відкрийте <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer">Google Cloud Console</a></li>
                    <li>Створіть новий проект або оберіть існуючий</li>
                    <li>Увімкніть <strong>Google Drive API</strong>:
                      <br /><Text type="secondary">APIs & Services → Library → шукайте "Google Drive API" → Enable</Text>
                    </li>
                    <li>Налаштуйте <strong>OAuth consent screen</strong>:
                      <br /><Text type="secondary">APIs & Services → OAuth consent screen → User type: External → заповніть назву додатку та email</Text>
                    </li>
                    <li>Додайте себе як <strong>тестового користувача</strong>:
                      <br /><Text type="secondary">На сторінці OAuth consent screen → секція Test users → + Add users → введіть свій Gmail → Save</Text>
                      <br /><Text type="secondary" italic>Це потрібно, бо додаток у режимі Testing і без цього Google заблокує вхід</Text>
                    </li>
                    <li>Створіть <strong>OAuth Client ID</strong>:
                      <br /><Text type="secondary">APIs & Services → Credentials → + Create Credentials → OAuth client ID</Text>
                    </li>
                    <li>Application type: <strong>Web application</strong></li>
                    <li>В <strong>Authorized redirect URIs</strong> додайте:
                      <br /><Text code copyable>http://localhost:8000/api/reports/backup/gdrive-callback/</Text>
                    </li>
                    <li>Натисніть <strong>Create</strong>, потім <strong>Download JSON</strong> (стрілка завантаження)</li>
                    <li>Збережіть завантажений JSON файл у папку <Text code>backend/</Text> вашого проекту</li>
                    <li>Створіть папку в Google Drive для бекапів:
                      <br /><Text type="secondary">Відкрийте Google Drive → Створити папку → Відкрийте її → Скопіюйте ID з URL (після folders/)</Text>
                    </li>
                    <li>Додайте в файл <Text code>.env</Text>:
                      <br /><Text code>GDRIVE_CREDENTIALS_PATH=назва_завантаженого_файлу.json</Text>
                      <br /><Text code>GDRIVE_FOLDER_ID=id_папки_з_url</Text>
                    </li>
                    <li>Перезапустіть сервер та натисніть кнопку <strong>"Авторизувати Google Drive"</strong> вище</li>
                  </ol>
                ),
              }]}
            />
          </>
        )}
      </Card>

      {/* Cloud Backup History */}
      {backupRecords.length > 0 && (
        <Card
          title={<><CloudServerOutlined /> Історія хмарних бекапів</>}
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={backupRecords}
            columns={cloudColumns}
            components={cloudComponents}
            rowKey="id"
            loading={backupRecordsLoading}
            size="small"
            pagination={{
              current: backupPage,
              total: backupRecordsTotal,
              pageSize: 20,
              onChange: (p) => { setBackupPage(p); loadBackupRecords(p) },
              showTotal: (t) => `Всього: ${t}`,
            }}
          />
        </Card>
      )}

      <Divider />

      {/* DB info */}
      <Title level={5} style={{ marginBottom: 16 }}>Локальний бекап бази даних</Title>

      <Alert
        message="Рекомендація"
        description="SQL формат рекомендується для повного відновлення бази, JSON — для міграції даних між системами."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {dbInfo && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="База даних"
                value={dbInfo.database_name}
                prefix={<DatabaseOutlined />}
                valueStyle={{ fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Розмір БД"
                value={dbInfo.database_size}
                prefix={<HddOutlined />}
                valueStyle={{ fontSize: 18 }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Таблиць"
                value={dbInfo.tables_count}
                prefix={<TableOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="Основних засобів"
                value={dbInfo.assets_count}
                prefix={<CloudServerOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Backup actions */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={<><FileTextOutlined style={{ marginRight: 8 }} />SQL бекап (pg_dump)</>}
            hoverable
          >
            <Paragraph type="secondary">
              Повна копія бази даних у форматі SQL. Включає структуру таблиць та всі дані.
              Підходить для відновлення бази за допомогою <Text code>psql</Text> або <Text code>pg_restore</Text>.
            </Paragraph>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Відновлення: <Text code>psql -U postgres -d buh_assets {'<'} backup.sql</Text>
              </Text>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={downloadingSql}
                onClick={() => handleDownload('sql')}
                size="large"
                block
              >
                Завантажити SQL бекап
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<><CodeOutlined style={{ marginRight: 8 }} />JSON бекап (Django)</>}
            hoverable
          >
            <Paragraph type="secondary">
              Експорт усіх даних у форматі JSON через Django. Не включає структуру таблиць,
              тільки дані. Підходить для міграції між середовищами.
            </Paragraph>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Відновлення: <Text code>python manage.py loaddata backup.json</Text>
              </Text>
              <Button
                icon={<DownloadOutlined />}
                loading={downloadingJson}
                onClick={() => handleDownload('json')}
                size="large"
                block
              >
                Завантажити JSON бекап
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Restore from file */}
      <Card
        title={<><UndoOutlined style={{ marginRight: 8 }} />Відновлення з файлу</>}
        style={{ marginBottom: 24 }}
      >
        <Alert
          message="Увага! Відновлення замінить поточні дані."
          description="Завантажте раніше створений бекап у форматі .sql або .json для відновлення бази даних. Рекомендуємо спочатку створити бекап поточного стану."
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Upload.Dragger
          accept=".sql,.json"
          multiple={false}
          showUploadList={false}
          disabled={restoreLoading}
          beforeUpload={(file) => {
            handleFileRestore(file as unknown as File)
            return false
          }}
        >
          <p className="ant-upload-drag-icon">
            {restoreLoading ? <SyncOutlined spin style={{ fontSize: 48, color: '#1677ff' }} /> : <UploadOutlined style={{ fontSize: 48, color: '#1677ff' }} />}
          </p>
          <p className="ant-upload-text">
            {restoreLoading ? 'Відновлення...' : 'Натисніть або перетягніть файл .sql / .json сюди'}
          </p>
          <p className="ant-upload-hint">
            Підтримуються формати: SQL (pg_dump) та JSON (Django dumpdata)
          </p>
        </Upload.Dragger>
      </Card>

      {/* Download history (session only) */}
      {history.length > 0 && (
        <Card title="Історія завантажень (поточна сесія)">
          {history.map((item, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 0',
                borderBottom: idx < history.length - 1 ? '1px solid #f0f0f0' : 'none',
              }}
            >
              <Space>
                {item.format === 'SQL' ? <FileTextOutlined /> : <CodeOutlined />}
                <Text>{item.filename}</Text>
              </Space>
              <Text type="secondary">{item.timestamp}</Text>
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}

export default BackupPage
