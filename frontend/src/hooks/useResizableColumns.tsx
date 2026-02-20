import React, { useState, useCallback } from 'react'
import { Resizable, ResizeCallbackData } from 'react-resizable'

/* ------------------------------------------------------------------ */
/*  ResizableTitle – замінює стандартний <th> для підтримки drag-resize */
/* ------------------------------------------------------------------ */
const ResizableTitle = (
  props: React.HTMLAttributes<HTMLTableCellElement> & {
    onResize?: (e: React.SyntheticEvent, data: ResizeCallbackData) => void
    width?: number
  },
) => {
  const { onResize, width, ...restProps } = props

  if (!width || !onResize) {
    return <th {...restProps} />
  }

  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="resizable-handle"
          onClick={(e) => e.stopPropagation()}
          style={{
            position: 'absolute',
            right: -5,
            bottom: 0,
            top: 0,
            width: 10,
            cursor: 'col-resize',
            zIndex: 1,
          }}
        />
      }
      onResize={onResize}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} />
    </Resizable>
  )
}

/* ------------------------------------------------------------------ */
/*  Hook: useResizableColumns                                          */
/*  Приймає масив колонок Ant Design (з підтримкою grouped children)   */
/*  Повертає { columns, components } для передачі в <Table />          */
/* ------------------------------------------------------------------ */

type AnyColumn = {
  dataIndex?: string
  key?: string
  width?: number
  children?: AnyColumn[]
  [k: string]: any
}

function getColKey(col: AnyColumn): string {
  return (col.dataIndex as string) || (col.key as string) || ''
}

function extractLeafWidths(cols: AnyColumn[]): Record<string, number> {
  const widths: Record<string, number> = {}
  const traverse = (columns: AnyColumn[]) => {
    columns.forEach((col) => {
      if (col.children) {
        traverse(col.children)
      } else {
        const key = getColKey(col)
        if (key && col.width) widths[key] = col.width
      }
    })
  }
  traverse(cols)
  return widths
}

export function useResizableColumns(initialColumns: AnyColumn[]) {
  const [widths, setWidths] = useState<Record<string, number>>(() =>
    extractLeafWidths(initialColumns),
  )

  const handleResize = useCallback(
    (colKey: string) =>
      (_: React.SyntheticEvent, { size }: ResizeCallbackData) => {
        setWidths((prev) => ({ ...prev, [colKey]: Math.max(size.width, 40) }))
      },
    [],
  )

  const applyResize = useCallback(
    (cols: AnyColumn[]): AnyColumn[] => {
      return cols.map((col) => {
        if (col.children) {
          return { ...col, children: applyResize(col.children) }
        }
        const key = getColKey(col)
        const w = widths[key] || col.width
        return {
          ...col,
          width: w,
          onHeaderCell: () => ({
            width: w,
            onResize: handleResize(key),
          }),
        }
      })
    },
    [widths, handleResize],
  )

  return {
    columns: applyResize(initialColumns),
    components: {
      header: { cell: ResizableTitle },
    },
  }
}
