import { api } from './api'
import type {
  EmailTemplate,
  EmailRecipient,
  EmailCampaign,
  CampaignStats,
  PaginatedResponse,
} from './types'

// === Templates ===

export function getTemplates(filters?: Record<string, string>) {
  return api.get<PaginatedResponse<EmailTemplate>>('/mailer/templates/', filters)
}

export function getTemplate(id: string) {
  return api.get<EmailTemplate>(`/mailer/templates/${id}/`)
}

export function createTemplate(data: Partial<EmailTemplate>) {
  return api.post<EmailTemplate>('/mailer/templates/', data)
}

export function updateTemplate(id: string, data: Partial<EmailTemplate>) {
  return api.patch<EmailTemplate>(`/mailer/templates/${id}/`, data)
}

export function deleteTemplate(id: string) {
  return api.delete<never>(`/mailer/templates/${id}/`)
}

export function previewTemplate(id: string, context: Record<string, string>) {
  return api.post<{ subject: string; body_html: string }>(`/mailer/templates/${id}/preview/`, { context })
}

export function uploadTemplateImage(file: File, altText = '') {
  const formData = new FormData()
  formData.append('image', file)
  if (altText) formData.append('alt_text', altText)
  return api.upload<{ id: string; url: string; alt_text: string; file_size: number }>('/mailer/images/', formData)
}

// === Recipients ===

export function getRecipients(filters?: Record<string, string>) {
  return api.get<PaginatedResponse<EmailRecipient>>('/mailer/recipients/', filters)
}

export function createRecipient(data: Partial<EmailRecipient>) {
  return api.post<EmailRecipient>('/mailer/recipients/', data)
}

export function bulkCreateRecipients(recipients: string[], source = 'manual') {
  return api.post<{ created: number; skipped: number }>('/mailer/recipients/bulk/', { recipients, source })
}

export function unsubscribeRecipient(id: string) {
  return api.delete<never>(`/mailer/recipients/${id}/`)
}

// === Campaigns ===

export function getCampaigns(filters?: Record<string, string>) {
  return api.get<PaginatedResponse<EmailCampaign>>('/mailer/campaigns/', filters)
}

export function getCampaign(id: string) {
  return api.get<EmailCampaign>(`/mailer/campaigns/${id}/`)
}

export function createCampaign(data: Partial<EmailCampaign>) {
  return api.post<EmailCampaign>('/mailer/campaigns/', data)
}

export function updateCampaign(id: string, data: Partial<EmailCampaign>) {
  return api.patch<EmailCampaign>(`/mailer/campaigns/${id}/`, data)
}

export function deleteCampaign(id: string) {
  return api.delete<never>(`/mailer/campaigns/${id}/`)
}

export function sendCampaign(id: string) {
  return api.post<{ total_recipients: number }>(`/mailer/campaigns/${id}/send/`)
}

export function getCampaignStats(id: string) {
  return api.get<CampaignStats>(`/mailer/campaigns/${id}/stats/`)
}


