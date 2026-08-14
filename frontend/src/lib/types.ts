export interface User {
  id: string
  username: string
  email: string
  first_name: string
  last_name: string
  phone: string
  organization: string | null
  organization_detail: Organization | null
  is_organization_admin: boolean
  is_active: boolean
  date_joined: string
}

export interface Organization {
  id: string
  name: string
  tax_id: string
  phone: string
  email: string
  is_active: boolean
  created_at: string
}

export interface Sector {
  id: string
  name: string
  description: string
  created_at: string
}

export interface Product {
  id: string
  name: string
  description: string
  sectors: string[]
  created_at: string
}

export interface Company {
  id: string
  name: string
  sector: string | null
  sector_name: string
  detected_sector: string
  score: number
  status: string
  city: string
  state: string
  is_lead: boolean
  is_client: boolean
  source: string
  created_at: string
  website: string
  contacts_count: number
  google_rating: number | null
  google_reviews_count: number | null
  maps_categories: string[]
  main_photo_url: string | null
  latitude: number | null
  longitude: number | null
  opening_hours: Record<string, unknown> | null
}

export interface CompanyDetail extends Company {
  organization: string | null
  business_name: string
  rfc: string
  description: string
  website: string
  email: string
  phone: string
  address: string
  country: string
  postal_code: string
  latitude: number | null
  longitude: number | null
  notes: string
  source_file: string
  contacts: CompanyContact[]
  updated_at: string
  analysis_score: number
  analysis_priority: string
  analysis_reason: string
  analysis_summary: string
  analysis_products: string[]
}

export interface CompanyContact {
  id: string
  company: string
  name: string
  position: string
  email: string
  phone: string
  is_primary: boolean
}

export interface Lead {
  id: string
  company: string
  company_name: string
  company_status: string
  contact: string | null
  contact_name: string
  contact_email: string
  score: number
  is_potential_client: boolean
  priority: string
  status: string
  stage: string
  stage_display: string
  esquema: string
  esquema_display: string
  monto_total: string | null
  unidad_interes: string
  last_email_interaction: string | null
  detected_sector: string
  recommended_products: string
  analysis_summary: string
  reason: string
  assigned_to: string | null
  assigned_to_name: string
  auto_created: boolean
  created_at: string
  updated_at: string
}

export interface Report {
  id: string
  title: string
  report_type: string
  status: string
  file: string | null
  file_type: string
  created_at: string
}

export interface ScrapingJobSummary {
  id: string
  search_query: string
  location: string
  status: string
  companies_count: number
  created_at: string
}

export interface SearchCompany {
  id: string
  name: string
  score: number
  sector: string | null
  sector_name: string
  detected_sector: string
  status: string
  city: string
  state: string
  is_lead: boolean
  is_client: boolean
  source: string
  created_at: string
  website: string
  contacts_count: number
  google_rating: number | null
  google_reviews_count: number | null
  maps_categories: string[]
  main_photo_url: string | null
  latitude: number | null
  longitude: number | null
  opening_hours: Record<string, unknown> | null
}

export interface DashboardSummary {
  total_companies: number
  total_analyzed: number
  total_pending: number
  total_errors: number
  total_leads: number
  potential_clients: number
  avg_score: number
  by_sector: { detected_sector: string; count: number }[]
  by_status: { status: string; count: number }[]
  by_priority: { priority: string; count: number }[]
}

export interface JobStats {
  total: number
  relevant: number
  discarded: number
  threshold: number
  avg_score: number
  by_priority: Record<string, number>
  credits_consumed?: number
  enriched_count?: number
}

export interface PreprocessingJob {
  id: string
  original_filename: string
  status: string
  total_records: number
  relevant_records: number
  filtered_records: number
  scoring_threshold: number
  cleaned_file: string | null
  stats_json: JobStats | null
  processing_time: number | null
  error_message: string
  auto_enrich_sql: boolean
  credits_consumed: number
  created_at: string
  updated_at: string
}

export interface PreprocessResponse {
  task_id: string
  job_id: string
  status: string
  filename: string
  threshold: number
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// === Inventario ===

export interface InventoryItem {
  id: string
  organization: string | null
  almacen_id: string
  producto_id: string
  sku_o_vin: string
  nombre_unidad: string
  cantidad_disponible: number
  tipo_movimiento: string
  updated_at: string
}

// === Email Marketing ===

export interface EmailTemplate {
  id: string
  organization: string | null
  name: string
  template_type: string
  subject: string
  body_html: string
  variables: string[]
  description: string
  is_active: boolean
  use_count: number
  created_at: string
  updated_at: string
}

export interface EmailRecipient {
  id: string
  organization: string | null
  company: string | null
  lead: string | null
  email: string
  first_name: string
  last_name: string
  company_name: string
  sector: string
  is_active: boolean
  unsubscribed_at: string | null
  source: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface EmailCampaign {
  id: string
  organization: string | null
  name: string
  template: string | null
  template_name: string
  subject: string
  body_html: string
  source_filter: string
  status: string
  scheduled_at: string | null
  sent_at: string | null
  total_recipients: number
  sent_count: number
  open_count: number
  click_count: number
  bounce_count: number
  unsubscribe_count: number
  created_at: string
  updated_at: string
}

export interface CampaignSend {
  id: string
  campaign: string
  recipient: string
  recipient_email: string
  recipient_name: string
  tracking_id: string
  status: string
  sent_at: string | null
  opened_at: string | null
  clicked_at: string | null
  error_message: string
  events: EmailEvent[]
  created_at: string
}

export interface EmailEvent {
  id: string
  campaign_send: string
  event_type: string
  user_agent: string
  ip_address: string | null
  url: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface CampaignStats {
  sent: number
  opens: number
  clicks: number
  bounces: number
  unsubscribes: number
  by_status: Record<string, number>
}

export interface MailerDashboard {
  total_campaigns: number
  total_sent: number
  open_rate: number
  click_rate: number
  recent_campaigns: EmailCampaign[]
}
