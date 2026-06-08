import base64
import csv
import io
import logging
import tempfile

import pandas as pd
from celery import shared_task

logger = logging.getLogger(__name__)

FIELD_KEYWORDS = {
    'name': [
        'nombre', 'razón social', 'razon social', 'denominación',
        'denominacion', 'empresa', 'compañía', 'compania',
        'titular', 'cliente', 'proveedor', 'prospecto',
        'name', 'company', 'business',
    ],
    'description': [
        'descripcion', 'descripción', 'giro', 'actividad',
        'description', 'detalle', 'rubro',
        'giro de la empresa', 'giro comercial', 'actividad economica',
        'actividad económica', 'objeto social',
    ],
    'website': [
        'sitio', 'web', 'website', 'url', 'página', 'pagina',
        'portal',
    ],
    'email': [
        'correo', 'email', 'mail', 'e-mail', 'electrónico',
        'electronico',
    ],
    'phone': [
        'teléfono', 'telefono', 'phone', 'tel', 'celular',
        'movil', 'móvil', 'contacto',
    ],
    'address': [
        'direccion', 'dirección', 'domicilio', 'calle', 'colonia',
        'address', 'ubicación', 'ubicacion',
    ],
    'city': [
        'ciudad', 'municipio', 'poblacion', 'población',
        'localidad', 'city', 'delegación', 'delegacion',
    ],
    'state': [
        'estado', 'entidad federativa', 'provincia',
        'departamento', 'region', 'región', 'state',
    ],
    'country': ['país', 'pais', 'country', 'nación', 'nacion'],
    'rfc': ['rfc', 'registro federal', 'contribuyentes', 'tax_id', 'cif', 'nit'],
    'contact_name': [
        'nombre', 'representante', 'contacto', 'apellido',
        'nombre completo',
    ],
    'contact_position': ['cargo', 'puesto', 'posición', 'position', 'rol'],
    'contact_phone': ['teléfono', 'telefono', 'celular', 'contacto'],
    'contact_email': ['correo', 'email', 'mail'],
}


def _match_column(col_name, keywords):
    from unidecode import unidecode
    col = unidecode(col_name.lower().strip())
    for kw in keywords:
        if kw in col:
            return True
    return False


def _find_value_in_columns(columns, row, field, default=''):
    keywords = FIELD_KEYWORDS.get(field, [])
    for col_name in columns:
        if _match_column(col_name, keywords):
            val = row[col_name]
            if val is not None and str(val).strip():
                return str(val).strip()
    return default


def _build_contact_name(columns, row):
    parts = []
    for col_name in columns:
        col_lower = col_name.lower()
        if 'nombre' in col_lower and 'representante' in col_lower:
            parts.append(str(row[col_name] or '').strip())
        elif 'apellido' in col_lower:
            parts.append(str(row[col_name] or '').strip())
    return ' '.join(p for p in parts if p)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_company_upload(self, filename, file_content, sector_id=None,
                           organization_id=None, user_id=None, threshold=0,
                           use_ai_fallback=False):
    if threshold > 0:
        from apps.preprocessing.tasks import process_with_preprocessing
        return process_with_preprocessing(
            filename, file_content,
            sector_id=sector_id,
            organization_id=organization_id,
            user_id=user_id,
            threshold=threshold,
            use_ai_fallback=use_ai_fallback,
        )

    from apps.companies.models import Company, Sector, CompanyContact

    sector = None
    if sector_id:
        try:
            sector = Sector.objects.get(id=sector_id)
        except Sector.DoesNotExist:
            pass

    created = 0
    errors = 0

    try:
        file_bytes = base64.b64decode(file_content)
        if filename.endswith('.csv'):
            reader = csv.DictReader(io.StringIO(file_bytes.decode('utf-8')))
            rows = list(reader)
        else:
            with tempfile.NamedTemporaryFile(suffix=filename) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                df = pd.read_excel(tmp.name, engine='openpyxl')
            rows = df.to_dict('records')

        if not rows:
            return {'created': 0, 'errors': 0, 'total': 0, 'error': 'Archivo vacío'}

        original_columns = list(rows[0].keys())
        logger.info(f'Columns found: {original_columns}')

        company_ids = []
        for row in rows:
            try:
                name = _find_value_in_columns(original_columns, row, 'name')
                if not name:
                    errors += 1
                    continue

                description = _find_value_in_columns(original_columns, row, 'description')
                website = _find_value_in_columns(original_columns, row, 'website')
                email = _find_value_in_columns(original_columns, row, 'email')
                phone = _find_value_in_columns(original_columns, row, 'phone')
                address = _find_value_in_columns(original_columns, row, 'address')
                city = _find_value_in_columns(original_columns, row, 'city')
                state = _find_value_in_columns(original_columns, row, 'state')
                country = _find_value_in_columns(original_columns, row, 'country', 'México')
                rfc = _find_value_in_columns(original_columns, row, 'rfc')

                company = Company.objects.create(**{
                    'name': name,
                    'description': description,
                    'website': website,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'city': city,
                    'state': state,
                    'country': country,
                    'rfc': rfc,
                    'sector': sector,
                    'organization_id': organization_id,
                    'source': filename,
                    'status': 'pending',
                })

                contact_name = _build_contact_name(original_columns, row)
                if contact_name:
                    CompanyContact.objects.create(
                        company=company,
                        name=contact_name,
                        email=_find_value_in_columns(original_columns, row, 'contact_email'),
                        phone=_find_value_in_columns(original_columns, row, 'contact_phone'),
                        is_primary=True,
                    )

                company_ids.append(company.id)
                created += 1
            except Exception as e:
                logger.error(f'Error creating company from row: {e}')
                errors += 1

        if created > 0 and user_id:
            logger.info(f'Auto-queuing Cerebras analysis for {created} companies')
            from apps.ai_engine.tasks import analyze_company
            for cid in company_ids:
                analyze_company.delay(cid)

    except Exception as e:
        logger.error(f'Error processing file {filename}: {e}')
        return {'created': created, 'errors': errors, 'error': str(e)}

    return {
        'created': created,
        'errors': errors,
        'total': created + errors,
    }
