import { api } from './api'
import type { InventoryItem, PaginatedResponse } from './types'

export function getInventoryItems(filters?: Record<string, string>) {
  return api.get<PaginatedResponse<InventoryItem>>('/v1/inventory/items/', filters)
}