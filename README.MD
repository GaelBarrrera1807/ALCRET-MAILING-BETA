# Industrial Prospecting AI Platform

Plataforma SaaS de prospección industrial B2B orientada a la automatización de búsqueda, clasificación y análisis de clientes potenciales para venta de remolques y equipos industriales.

---

# Objetivo del Proyecto

Automatizar el proceso de prospección comercial mediante inteligencia artificial para:

- Analizar empresas automáticamente
- Detectar posibles compradores
- Clasificar leads por prioridad
- Recomendar productos industriales
- Encontrar contactos potenciales
- Generar reportes PDF
- Almacenar resultados en base de datos

---

# Productos Comercializados

La empresa comercializa los siguientes productos industriales:

- Dolly
- Cajas secas
- Plataformas
- Plataforma multimodal
- Portacontenedores
- Porta contenedor extensible
- Volteos
- Tolvas
- Tanques
- Sobre chasis
- Equipos especiales

---

# Sectores Objetivo

Los sectores con mayor prioridad comercial son:

- Transporte de carga general
- Construcción
- Agrícola
- Alimentos
- Petrolera
- Petroquímica
- Refresquera
- Portuaria

---

# Problema a Resolver

Actualmente el proceso de prospección comercial es manual:

1. Buscar empresas
2. Revisar si son clientes potenciales
3. Buscar contactos
4. Clasificar prioridades
5. Generar reportes

Este proceso consume mucho tiempo y dificulta escalar operaciones comerciales.

La plataforma busca automatizar este flujo utilizando inteligencia artificial.

---

# Funcionalidades Principales

## 1. Carga Masiva de Directorios

El usuario podrá subir:

- CSV
- Excel
- Directorios empresariales
- Bases de datos de empresas
- Scraping de Google Maps
- Directorios industriales

---

## 2. Limpieza y Normalización

El sistema deberá:

- Eliminar duplicados
- Limpiar teléfonos
- Validar dominios
- Normalizar datos
- Estandarizar nombres

---

## 3. Clasificación Inteligente con IA

La IA analizará:

- Giro empresarial
- Descripción del negocio
- Sitio web
- Actividad industrial
- Logística
- Infraestructura
- Operaciones

Y determinará:

- Probabilidad de compra
- Sector detectado
- Productos recomendados
- Prioridad comercial

---

## 4. Sistema de Scoring

Cada empresa recibirá un score de 1-100.

Factores importantes:

- Transporte pesado
- Flotillas
- Logística multimodal
- Operaciones industriales
- Puertos
- Contenedores
- Construcción
- Maquinaria
- Hidrocarburos
- Operaciones agrícolas

---

## 5. Enriquecimiento de Datos

El sistema podrá:

- Buscar sitios web
- Obtener dominios
- Extraer teléfonos
- Detectar redes sociales
- Obtener ubicación

---

## 6. Generación de Reportes

El sistema generará:

- PDF de leads
- Reportes de scoring
- Métricas comerciales
- Estadísticas de procesamiento

---

# Arquitectura Tecnológica

## Backend

- Django
- Django REST Framework
- Celery
- Redis
- PostgreSQL

---

## Frontend

- Next.js
- TailwindCSS

---

## Inteligencia Artificial

- Cerebras API
- Modelos LLM compatibles OpenAI SDK

---

## Infraestructura

- Docker
- Railway / VPS
- Nginx
- Gunicorn

---

# Arquitectura General del Sistema

```text
Usuario sube CSV
↓
Sistema limpia datos
↓
Worker procesa empresas
↓
IA analiza compañías
↓
Sistema asigna score
↓
Resultados se guardan en PostgreSQL
↓
Se generan reportes PDF
```

---

# Arquitectura Django

```text
apps/
│
├── users/          → Organización multiempresa + usuarios
├── core/           → Company, CompanyContact, Sector, Product (tablas históricas `companies_*`)
├── leads/          → Lead + LeadNote (scoring, prioridad, estado comercial)
├── ai_engine/      → Análisis con IA (Cerebras), AnalysisRequest/Result, PromptTemplate
├── scraping/       → ScrapingJob + ScrapedData (web, phone, social, Google Maps)
├── preprocessing/  → PreprocessingJob + PreprocessingRule (limpieza, filtrado, scoring)
├── mailer/         → EmailTemplate, EmailRecipient, EmailCampaign, CampaignSend, EmailEvent (Amazon SES)
├── analytics/      → DashboardMetric + ProcessingStats
├── companies/      → ⚠️ Stub de compatibilidad (re-exporta modelos desde core)
└── reports/        → Reportes PDF (módulo aislado)
```

---

# Descripción de Módulos

## users

- Autenticación
- Roles
- Multiempresa (Organization como tenant raíz)
- Permisos

---

## core

- Company: empresa con datos de contacto, scoring, geolocalización, índices compuestos
- CompanyContact: contactos de empresa
- Sector: sectores industriales (relacionado con Company vía FK)
- Product: productos con relación M2M a Sector
- Nota: tablas físicas `companies_*` por compatibilidad histórica

---

## leads

- Lead: lead con scoring, prioridad, estado comercial, O2O opcional con Company
- LeadNote: notas de seguimiento por lead
- Scoring y clasificación por prioridad (baja/media/alta/urgente)

---

## ai_engine

- Análisis con IA (Cerebras / LLMs compatibles OpenAI SDK)
- AnalysisRequest → solicitud, AnalysisResult → resultado (O2O)
- PromptTemplate: plantillas configurables (system prompt, temperature, model)

---

## scraping

- ScrapingJob: registro de trabajo (website, phone, social, enrichment, MAPS_DISCOVERY)
- ScrapedData: datos scrapeados vinculados a Company
- Company.scraping_job (FK) como única relación directa

---

## preprocessing

- PreprocessingJob: procesamiento de archivos CSV/Excel con pipeline configurable
- PreprocessingRule: reglas de industria/producto/exclusión con keywords y peso
- Pipeline: limpieza → clasificación → scoring → filtrado

---

## mailer

- EmailTemplate: plantillas con variables {{ }}, tipos (cold_outreach, marketing, etc.)
- EmailRecipient: destinatarios, vinculados a Lead (sin FK directa a Company)
- EmailCampaign: campañas con programación y tracking de métricas
- CampaignSend: envío individual con ses_message_id para SES webhooks
- EmailEvent: eventos de tracking (open, click, bounce, complaint, unsubscribe)

---

## analytics

- DashboardMetric: métricas del dashboard por organización y fecha
- ProcessingStats: estadísticas resumidas de procesamiento

---

# Arquitectura de Base de Datos (ERD)

Diagrama Entidad-Relación de los modelos activos (excluye stubs `companies` y `reports`):

```mermaid
erDiagram
    %% ═══════════════════════════════════════════════════════════════
    %% NOTA: Todos los modelos concretos heredan de BaseModel
    %% (abstracto), que hereda de TimeStampedModel + UUIDModel:
    %%   TimeStampedModel -> created_at, updated_at
    %%   UUIDModel        -> id UUID (PK autogenerado)
    %% ═══════════════════════════════════════════════════════════════

    %% ── App: users ────────────────────────────────────────────────
    Organization {
        string    name
        string    tax_id        "RFC"
        string    phone
        string    email
        boolean   is_active
    }

    User {
        string    username
        string    password
        string    first_name
        string    last_name
        string    email
        boolean   is_active
        boolean   is_staff
        boolean   is_superuser
        string    phone
        boolean   is_organization_admin
    }

    %% ── App: core (db_table='companies_*') ────────────────────────
    Sector {
        string    name            "UK"
        text      description
    }

    Product {
        string    name            "UK"
        text      description
    }

    Company {
        string    name
        string    business_name   "Razon social"
        string    rfc
        text      description
        url       website
        email     email
        string    phone
        text      address
        string    city
        string    state
        string    country
        string    postal_code
        float     latitude        "nullable"
        float     longitude       "nullable"
        string    detected_sector
        int       score
        boolean   is_client
        boolean   is_lead
        enum      status          "pending | analyzing | analyzed | error"
        text      notes
        string    source
        string    source_file
        float     google_rating   "nullable"
        int       google_reviews_count "nullable"
        json      maps_categories
        json      opening_hours
        url       main_photo_url  "nullable"
    }

    CompanyContact {
        string    name
        string    position
        email     email
        string    phone
        boolean   is_primary
    }

    %% ── App: leads ────────────────────────────────────────────────
    Lead {
        int       score
        boolean   is_potential_client
        enum      priority        "baja | media | alta | urgente"
        string    detected_sector
        text      recommended_products
        text      analysis_summary
        text      reason
        enum      status          "new | contacted | qualified | proposal | negotiation | won | lost"
        datetime  contacted_at    "nullable"
        datetime  last_contact    "nullable"
        datetime  next_follow_up  "nullable"
        text      notes
        boolean   auto_created
    }

    LeadNote {
        text      content
    }

    %% ── App: ai_engine ────────────────────────────────────────────
    AnalysisRequest {
        enum      status          "pending | processing | completed | error"
        text      prompt_used
        json      raw_response    "nullable"
        text      error_message
        float     processing_time "segundos (nullable)"
    }

    AnalysisResult {
        int       score
        boolean   is_potential_client
        string    detected_sector
        json      recommended_products
        text      reason
        enum      priority        "baja | media | alta | urgente"
        text      summary
        json      raw_json        "nullable"
    }

    PromptTemplate {
        string    name            "UK"
        text      description
        text      system_prompt
        text      user_prompt_template
        string    model
        float     temperature
        int       max_tokens
        boolean   is_active
        int       version
    }

    %% ── App: scraping ─────────────────────────────────────────────
    ScrapingJob {
        url       url
        enum      job_type        "website | phone | social | enrichment | MAPS_DISCOVERY"
        enum      status          "pending | processing | completed | error"
        json      result          "nullable"
        text      error_message
        int       credits_consumed
    }

    ScrapedData {
        string    source
        string    data_type
        json      raw_data        "nullable"
        json      processed_data  "nullable"
    }

    %% ── App: preprocessing ────────────────────────────────────────
    PreprocessingJob {
        string    original_filename
        enum      status          "pending | processing | completed | error"
        int       total_records
        int       relevant_records
        int       filtered_records
        int       scoring_threshold
        file      cleaned_file    "nullable"
        json      stats_json
        float     processing_time "nullable"
        text      error_message
        boolean   auto_enrich_sql
        int       credits_consumed
    }

    PreprocessingRule {
        string    name
        enum      rule_type       "industry | product | exclusion | custom"
        json      keywords
        int       weight
        json      recommended_products
        boolean   is_active
        text      description
    }

    %% ── App: mailer (Amazon SES) ──────────────────────────────────
    EmailTemplate {
        string    name
        enum      template_type   "cold_outreach | marketing | follow_up | newsletter | welcome | custom"
        string    subject
        text      body_html
        json      variables
        text      description
        boolean   is_active
        int       use_count
    }

    EmailRecipient {
        email     email
        string    first_name
        string    last_name
        string    company_name
        string    sector
        boolean   is_active
        datetime  unsubscribed_at "nullable"
        string    source
        json      metadata
    }

    EmailCampaign {
        string    name
        string    subject
        text      body_html
        enum      source_filter   "all | internal | external | manual"
        enum      status          "draft | scheduled | sending | sent | paused | cancelled"
        datetime  scheduled_at    "nullable"
        datetime  sent_at         "nullable"
        int       total_recipients
        int       sent_count
        int       open_count
        int       click_count
        int       bounce_count
        int       unsubscribe_count
    }

    CampaignSend {
        uuid      tracking_id     "UK"
        string    ses_message_id  "SES message ID (db_index, nullable)"
        enum      status          "pending | sent | delivered | opened | clicked | bounced | complained | unsubscribed"
        datetime  sent_at         "nullable"
        datetime  opened_at       "nullable"
        datetime  clicked_at      "nullable"
        text      error_message
    }

    TemplateImage {
        file      image
        string    alt_text
        int       file_size
    }

    EmailEvent {
        enum      event_type      "open | click | bounce | complaint | unsubscribe"
        text      user_agent
        ip        ip_address      "nullable"
        url       url
        json      metadata
    }

    %% ── App: analytics ────────────────────────────────────────────
    DashboardMetric {
        string    metric_type     "enum: total_companies, total_leads, avg_score, ..."
        json      value
        date      date
    }

    ProcessingStats {
        int       total_companies
        int       total_analyzed
        int       total_pending
        int       total_errors
        int       total_leads
        int       total_potential_clients
        float     avg_score
        date      date
    }

    %% ═══════════════════════════════════════════════════════════════
    %%  RELACIONES
    %% ═══════════════════════════════════════════════════════════════

    %% users
    Organization  ||--o{ User                : "users"
    Organization  ||--o{ Company             : "companies"
    Organization  ||--o{ Lead                : "leads"
    Organization  ||--o{ AnalysisRequest     : "analysis_requests"
    Organization  ||--o{ ScrapingJob         : "scraping_jobs"
    Organization  ||--o{ PreprocessingJob    : ""
    Organization  ||--o{ EmailTemplate       : "email_templates"
    Organization  ||--o{ EmailRecipient      : "email_recipients"
    Organization  ||--o{ EmailCampaign       : "email_campaigns"
    Organization  ||--o{ TemplateImage       : "template_images"
    Organization  ||--o{ DashboardMetric     : "metrics"
    Organization  ||--o{ ProcessingStats     : "processing_stats"

    User          ||--o{ LeadNote            : ""
    User          ||--o{ Lead                : "assigned_leads"

    %% core
    Sector        ||--o{ Company             : "companies"
    Sector        ||--o{ PreprocessingRule   : ""
    Product       }o--o{ Sector              : "sectors"

    ScrapingJob   ||--o{ Company             : "companies"

    Company       ||--o{ CompanyContact      : "contacts"
    Company       ||--o| Lead                : "lead"
    Company       ||--o{ AnalysisRequest     : "analysis_requests"
    Company       ||--o{ AnalysisResult      : "analysis_results"
    Company       ||--o{ ScrapedData         : "scraped_data"

    CompanyContact ||--o{ Lead               : "leads"

    %% leads
    Lead          ||--o{ LeadNote            : "notes_list"
    Lead          ||--o{ EmailRecipient      : "email_recipients"

    %% ai_engine
    AnalysisRequest ||--|| AnalysisResult    : "result"

    %% mailer
    EmailTemplate ||--o{ EmailCampaign       : "campaigns"
    EmailCampaign ||--o{ CampaignSend        : "sends"
    EmailRecipient ||--o{ CampaignSend       : "campaign_sends"
    CampaignSend  ||--o{ EmailEvent          : "events"
```

---

# Reglas de Clasificación IA

La IA deberá asignar score alto a empresas que mencionen:

- Transporte pesado
- Logística
- Contenedores
- Flotillas
- Carga industrial
- Operaciones portuarias
- Construcción
- Hidrocarburos
- Petroquímica
- Maquinaria pesada
- Operaciones agrícolas

La IA deberá asignar score bajo a:

- Retail pequeño
- Negocios administrativos
- Comercios locales pequeños
- Empresas sin actividad logística

---

# Reglas de Recomendación de Productos

## Transporte

Productos recomendados:
- Cajas secas
- Plataformas
- Portacontenedores
- Dolly

---

## Construcción

Productos recomendados:
- Volteos
- Plataformas
- Equipos especiales

---

## Petrolera / Petroquímica

Productos recomendados:
- Tanques
- Plataformas
- Equipos especiales

---

## Agrícola

Productos recomendados:
- Tolvas
- Plataformas
- Volteos

---

## Portuaria

Productos recomendados:
- Portacontenedores
- Plataforma multimodal
- Porta contenedor extensible

---

# Formato de Respuesta IA

La IA deberá responder SIEMPRE en formato JSON:

```json
{
  "empresa": "",
  "sector_detectado": "",
  "score": 0,
  "cliente_potencial": true,
  "productos_recomendados": [],
  "motivo": "",
  "prioridad": "alta"
}
```

---

# Ejemplos de Clasificación

## Empresa Buena

Nombre:
Transportes del Golfo

Descripción:
Empresa especializada en logística pesada, carga multimodal y transporte portuario.

Resultado esperado:

- Score alto
- Cliente potencial
- Recomendar plataformas
- Recomendar portacontenedores

---

## Empresa Mala

Nombre:
Cafetería Centro

Descripción:
Venta de café y alimentos.

Resultado esperado:

- Score bajo
- No cliente potencial
- Sin productos recomendados

---

# Base de Datos

El sistema deberá almacenar:

- Empresas procesadas
- Score IA
- Productos recomendados
- Sectores detectados
- Historial de análisis
- PDFs generados
- Resultados de procesamiento

---

# Variables de Entorno

```env
DEBUG=True

SECRET_KEY=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

REDIS_URL=

CEREBRAS_API_KEY=
```

---

# Integración Cerebras

La aplicación utilizará Cerebras como motor principal de IA.

La IA será utilizada para:

- Clasificación de empresas
- Análisis semántico
- Recomendación de productos
- Generación de scoring
- Priorización comercial

---

# Objetivo Final

Construir una plataforma inteligente de prospección industrial capaz de:

- Reducir trabajo manual
- Mejorar calidad de leads
- Automatizar clasificación empresarial
- Generar reportes automáticamente
- Escalar operaciones comerciales
- Optimizar prospección B2B industrial