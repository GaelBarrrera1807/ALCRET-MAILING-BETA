# Industrial Prospecting AI Platform

## Backend (Django 6.0.5 + DRF)

### Modelos
- `users.User` - Usuario con herencia de AbstractUser + organización
- `users.Organization` - Tenant multiempresa
- `companies.Sector` - Sectores industriales
- `companies.Product` - Productos con relación a sectores
- `companies.Company` - Empresa con datos de contacto y scoring
- `companies.CompanyContact` - Contactos de empresa
- `leads.Lead` - Lead con scoring, prioridad y estado comercial
- `leads.LeadNote` - Notas de seguimiento de leads
- `ai_engine.AnalysisRequest` - Solicitud de análisis a IA
- `ai_engine.AnalysisResult` - Resultado del análisis
- `ai_engine.PromptTemplate` - Plantillas de prompts
- `scraping.ScrapingJob` - Trabajos de scraping
- `scraping.ScrapedData` - Datos scrapeados
- `analytics.DashboardMetric` - Métricas del dashboard
- `analytics.ProcessingStats` - Estadísticas de procesamiento
- `reports.Report` - Reportes generados
- `reports.ReportTemplate` - Plantillas de reportes

### API Endpoints
- `POST /api/auth/login/` - JWT login
- `POST /api/auth/register/` - Registro
- `POST /api/auth/token/refresh/` - Refresh token
- `GET/POST/PATCH/DELETE /api/users/` - CRUD usuarios
- `GET /api/users/me/` - Usuario actual
- `GET/POST/PATCH/DELETE /api/companies/` - CRUD empresas
- `POST /api/companies/upload/` - Subir CSV/Excel
- `POST /api/companies/{id}/analyze/` - Analizar empresa
- `GET/POST/PATCH/DELETE /api/leads/` - CRUD leads
- `POST /api/leads/batch_update/` - Actualización masiva
- `GET/POST/PATCH/DELETE /api/sectors/` - CRUD sectores
- `GET/POST/PATCH/DELETE /api/products/` - CRUD productos
- `GET /api/analysis-results/` - Resultados de análisis
- `GET /api/summary/` - Resumen del dashboard
- `POST /api/reports/` - Generar reporte
- `GET /api/docs/` - Swagger UI
- `GET /api/schema/` - OpenAPI schema
- `GET /api/health/` - Health check

### Tareas Celery
- `analyze_company` - Analizar empresa con IA
- `process_company_upload` - Procesar CSV/Excel
- `run_scraping_job` - Ejecutar scraping
- `generate_report` - Generar reporte PDF

### Comandos útiles
```bash
# Migraciones
docker-compose run --rm backend python manage.py makemigrations
docker-compose run --rm backend python manage.py migrate

# Shell
docker-compose run --rm backend python manage.py shell

# Crear superusuario
docker-compose run --rm backend python manage.py createsuperuser

# Tests
docker-compose run --rm backend python manage.py test

# Logs del worker
docker-compose logs -f worker

# Logs del backend
docker-compose logs -f backend

# Reconstruir
docker-compose build --no-cache backend
```

## Frontend (Next.js 16.2.6 + React 19 + Tailwind v4)

### Páginas
- `/login` - Inicio de sesión
- `/register` - Registro de usuario
- `/dashboard` - Dashboard con métricas
- `/companies` - Lista de empresas con upload
- `/leads` - Lista de leads con filtros
- `/reports` - Generación y descarga de reportes
