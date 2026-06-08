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
├── users/
├── companies/
├── leads/
├── ai_engine/
├── scraping/
├── analytics/
├── reports/
└── core/
```

---

# Descripción de Módulos

## users

- Autenticación
- Roles
- Multiempresa
- Permisos

---

## companies

- Empresas
- Sectores
- Información comercial

---

## leads

- Leads
- Scoring
- Prioridades
- Estado comercial

---

## ai_engine

- Integración Cerebras
- Prompts
- Clasificación IA
- Recomendación de productos

---

## scraping

- Extracción de información
- Sitios web
- Teléfonos
- Redes sociales

---

## reports

- PDFs
- Exportaciones
- Reportes comerciales

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