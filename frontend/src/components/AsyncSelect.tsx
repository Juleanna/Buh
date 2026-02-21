import React, { useState, useRef, useCallback, useEffect } from 'react'
import { Select, Spin } from 'antd'
import type { SelectProps } from 'antd'
import api from '../api/client'

export interface AsyncSelectProps extends Omit<SelectProps, 'options' | 'onSearch' | 'filterOption' | 'loading'> {
  /** API endpoint, e.g. '/assets/items/' */
  url: string
  /** Extra query params sent with every request, e.g. { status: 'active', no_receipt: 1 } */
  params?: Record<string, unknown>
  /** Map API result item → { value, label }. Receives raw item from API. */
  mapOption: (item: any) => { value: number; label: string }
  /** How many items to fetch per request (default 50) */
  pageSize?: number
  /** Debounce delay in ms (default 350) */
  debounceMs?: number
}

/**
 * Ant Design Select with server-side search.
 * - Loads first N items on dropdown open
 * - Searches via API as user types (debounced)
 * - Works with paginated DRF responses
 */
const AsyncSelect: React.FC<AsyncSelectProps> = ({
  url,
  params = {},
  mapOption,
  pageSize = 50,
  debounceMs = 350,
  ...selectProps
}) => {
  const [options, setOptions] = useState<{ value: number; label: string }[]>([])
  const [fetching, setFetching] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSearchRef = useRef('')

  const fetchOptions = useCallback(async (search: string) => {
    lastSearchRef.current = search
    setFetching(true)
    try {
      const queryParams: Record<string, unknown> = {
        ...params,
        page_size: pageSize,
      }
      if (search) queryParams.search = search
      const { data } = await api.get(url, { params: queryParams })
      const results: any[] = data.results || data
      // Only apply if this is still the latest search
      if (search === lastSearchRef.current) {
        setOptions(results.map(mapOption))
      }
    } catch {
      // ignore
    } finally {
      if (search === lastSearchRef.current) {
        setFetching(false)
      }
    }
  }, [url, JSON.stringify(params), pageSize, mapOption])

  const handleSearch = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => {
      fetchOptions(value)
    }, debounceMs)
  }, [fetchOptions, debounceMs])

  const handleDropdownOpen = useCallback((open: boolean) => {
    if (open && options.length === 0) {
      fetchOptions('')
    }
  }, [fetchOptions, options.length])

  // If value is set (e.g. editing), ensure we load options so the label resolves
  useEffect(() => {
    if (selectProps.value != null && options.length === 0) {
      fetchOptions('')
    }
  }, [selectProps.value])

  return (
    <Select
      showSearch
      filterOption={false}
      onSearch={handleSearch}
      onOpenChange={handleDropdownOpen}
      loading={fetching}
      options={options}
      notFoundContent={fetching ? <Spin size="small" /> : undefined}
      {...selectProps}
    />
  )
}

export default AsyncSelect
