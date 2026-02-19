export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  patronymic: string
  role: 'admin' | 'accountant' | 'inventory_manager'
  position: string
  phone: string
  full_name: string
  is_active: boolean
}

export interface Location {
  id: number
  name: string
  is_active: boolean
  assets_count?: number
}

export interface ResponsiblePerson {
  id: number
  ipn: string
  full_name: string
  position: string
  location: number | null
  location_name: string
  is_active: boolean
  assets_count?: number
}

export interface TurnoverRow {
  index: number
  responsible_person_name: string
  account_number: string
  name: string
  inventory_number: string
  unit_of_measure: string
  cost: string
  opening_qty: number
  opening_amount: string
  debit_qty: number
  debit_amount: string
  credit_qty: number
  credit_amount: string
  closing_qty: number
  closing_amount: string
}

export interface AssetGroup {
  id: number
  code: string
  name: string
  min_useful_life_months: number | null
  account_number: string
  depreciation_account: string
  assets_count?: number
}

export type DepreciationMethod =
  | 'straight_line'
  | 'reducing_balance'
  | 'accelerated_reducing'
  | 'cumulative'
  | 'production'

export type AssetStatus = 'active' | 'disposed' | 'conserved'

export interface Asset {
  id: number
  inventory_number: string
  name: string
  group: number
  group_name: string
  status: AssetStatus
  status_display: string
  initial_cost: string
  residual_value: string
  incoming_depreciation: string
  current_book_value: string
  accumulated_depreciation: string
  depreciation_method: DepreciationMethod
  depreciation_method_display: string
  useful_life_months: number
  total_production_capacity: string | null
  commissioning_date: string
  depreciation_start_date: string
  disposal_date: string | null
  responsible_person: number | null
  responsible_person_name: string
  location: number | null
  location_name: string
  description: string
  quantity: number
  factory_number: string
  passport_number: string
  manufacture_year: number | null
  unit_of_measure: string
  depreciation_rate: string | null
  created_by: number | null
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface AssetReceipt {
  id: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  receipt_type: string
  receipt_type_display: string
  document_number: string
  document_date: string
  supplier: string
  supplier_organization: number | null
  supplier_organization_name: string
  amount: string
  notes: string
  created_by: number | null
  created_at: string
}

export interface AssetDisposal {
  id: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  disposal_type: string
  disposal_type_display: string
  document_number: string
  document_date: string
  reason: string
  sale_amount: string
  book_value_at_disposal: string
  accumulated_depreciation_at_disposal: string
  notes: string
  created_by: number | null
  created_at: string
}

export interface DepreciationRecord {
  id: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  period_year: number
  period_month: number
  depreciation_method: DepreciationMethod
  method_display: string
  amount: string
  book_value_before: string
  book_value_after: string
  production_volume: string | null
  is_posted: boolean
  created_by: number | null
  created_at: string
  account_number: string
  expense_account: string
  asset_initial_cost: string
  asset_residual_value: string
  asset_depreciation_rate: string | null
  asset_useful_life_months: number
  asset_incoming_depreciation: string
}

export interface Inventory {
  id: number
  number: string
  date: string
  order_number: string
  order_date: string
  status: 'draft' | 'in_progress' | 'completed'
  status_display: string
  location: number | null
  location_name: string
  notes: string
  commission_head: number | null
  commission_head_name: string
  commission_members: number[]
  items_count?: number
  items?: InventoryItem[]
  created_by: number | null
  created_at: string
}

export interface InventoryItem {
  id: number
  inventory: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  is_found: boolean
  condition: 'good' | 'needs_repair' | 'unusable'
  condition_display: string
  book_value: string
  actual_value: string | null
  difference: string
  notes: string
}

export interface Organization {
  id: number
  name: string
  short_name: string
  edrpou: string
  address: string
  director: string
  accountant: string
  is_active: boolean
  is_own: boolean
}

export interface AccountEntry {
  id: number
  entry_type: string
  entry_type_display: string
  date: string
  debit_account: string
  credit_account: string
  amount: string
  description: string
  asset: number
  asset_name: string
  asset_inventory_number: string
  document_number: string
  document_date: string | null
  is_posted: boolean
  created_by: number | null
  created_by_name: string
  created_at: string
}

export interface AssetRevaluation {
  id: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  revaluation_type: 'upward' | 'downward'
  revaluation_type_display: string
  date: string
  document_number: string
  old_initial_cost: string
  old_depreciation: string
  old_book_value: string
  fair_value: string
  new_initial_cost: string
  new_depreciation: string
  new_book_value: string
  revaluation_amount: string
  notes: string
  created_by: number | null
  created_at: string
}

export interface AssetImprovement {
  id: number
  asset: number
  asset_name: string
  asset_inventory_number: string
  improvement_type: string
  improvement_type_display: string
  date: string
  document_number: string
  description: string
  amount: string
  contractor: string
  increases_value: boolean
  expense_account: string
  notes: string
  created_by: number | null
  created_at: string
}

export interface AssetAttachment {
  id: number
  asset: number
  file: string
  file_type: string
  file_type_display: string
  name: string
  description: string
  file_size: number
  uploaded_by: number | null
  uploaded_by_name: string
  uploaded_at: string
}

export interface AuditLogEntry {
  id: number
  user: number | null
  user_name: string
  action: string
  action_display: string
  content_type: number
  content_type_name: string
  object_id: number
  object_repr: string
  changes: Record<string, unknown>
  ip_address: string | null
  timestamp: string
}

export interface Notification {
  id: number
  recipient: number
  notification_type: string
  notification_type_display: string
  title: string
  message: string
  asset: number | null
  is_read: boolean
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface DashboardData {
  assets: {
    total: number
    active: number
    disposed: number
    conserved: number
  }
  financials: {
    total_initial_cost: string
    total_book_value: string
    total_depreciation: string
  }
  by_group: Array<{
    group__code: string
    group__name: string
    count: number
    total_initial: string
    total_book: string
  }>
  depreciation_by_method: Array<{
    depreciation_method: DepreciationMethod
    count: number
  }>
}
