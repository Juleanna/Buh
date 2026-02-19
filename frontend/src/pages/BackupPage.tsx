import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Typography, Statistic, Space, Alert, Spin } from 'antd'
import { message } from '../utils/globalMessage'
import {
  DatabaseOutlined,
  DownloadOutlined,
  CloudServerOutlined,
  TableOutlined,
  HddOutlined,
  FileTextOutlined,
  CodeOutlined,
} from '@ant-design/icons'
import api from '../api/client'

const { Title, Text, Paragraph } = Typography

interface DbInfo {
  database_name: string
  database_host: string
  database_size: string
  tables_count: number
  assets_count: number
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

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>Резервне копіювання бази даних</Title>

      <Alert
        message="Рекомендація"
        description="Регулярно створюйте резервні копії бази даних та зберігайте їх у безпечному місці. SQL формат рекомендується для повного відновлення бази, JSON — для міграції даних між системами."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      {/* DB info */}
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
