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
  score: number
  is_potential_client: boolean
  priority: string
  status: string
  detected_sector: string
  recommended_products: string
  analysis_summary: string
  reason: string
  assigned_to: string | null
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

export interface PreprocessingJob {
  id: string
  original_filename: string
  status: string
  total_records: number
  relevant_records: number
  filtered_records: number
  scoring_threshold: number
  cleaned_file: string | null
  stats_json: {
    total: number
    relevant: number
    discarded: number
    threshold: number
    avg_score: number
    by_priority: Record<string, number>
  }
  processing_time: number | null
  error_message: string
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
