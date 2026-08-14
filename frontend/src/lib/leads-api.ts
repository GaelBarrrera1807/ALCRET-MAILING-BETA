import { api } from './api'
import type { Lead, PaginatedResponse } from './types'

export function getLeads(filters?: Record<string, string>) {
  return api.get<PaginatedResponse<Lead>>('/leads/', filters)
}

export function updateLeadStage(id: string, stage: string) {
  return api.patch<Lead>(`/leads/${id}/`, { stage })
}