import logging
import re
import unicodedata

from unidecode import unidecode

logger = logging.getLogger(__name__)


def keyword_match(text, keyword):
    """
    Flexible keyword matching.
    Single word (>4 chars): simple substring (handles plurals naturally).
    Single word (<=4 chars): word boundary match only (prevents false positives).
    Multi-word: allows one word between terms (catches 'de', 'para', 'en', etc.)
    and matches word prefixes (catches plural forms).
    """
    parts = keyword.split()
    if len(parts) == 1:
        if len(keyword) <= 4:
            return bool(re.search(rf'\b{re.escape(keyword)}\b', text))
        return keyword in text
    pattern_parts = []
    for part in parts:
        pattern_parts.append(r'\b' + re.escape(part) + r'\w*\b')
    pattern = pattern_parts[0]
    for i in range(1, len(pattern_parts)):
        pattern += r'\s+(?:\w+\s+)?' + pattern_parts[i]
    return bool(re.search(pattern, text))


FIELD_KEYWORDS = {
    'name': [
        'nombre', 'razón social', 'razon social', 'denominación',
        'denominacion', 'empresa', 'compañía', 'compania',
        'titular', 'cliente', 'proveedor', 'prospecto',
        'name', 'company', 'business',
    ],
    'description': [
        'descripcion', 'descripción', 'giro', 'actividad',
        'description', 'detalle', 'rubro', 'giro comercial',
    ],
    'website': [
        'sitio', 'web', 'website', 'url', 'página', 'pagina', 'portal',
    ],
    'email': [
        'correo', 'email', 'mail', 'e-mail', 'electrónico', 'electronico',
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
        'nombre', 'representante', 'contacto', 'apellido', 'nombre completo',
    ],
    'contact_position': ['cargo', 'puesto', 'posición', 'position', 'rol'],
    'contact_phone': ['teléfono', 'telefono', 'celular', 'contacto'],
    'contact_email': ['correo', 'email', 'mail'],
}


class DataCleaner:
    def clean(self, rows, original_columns=None):
        if original_columns is None:
            original_columns = list(rows[0].keys()) if rows else []
        cleaned = []
        seen = set()
        for row in rows:
            normalized = self._normalize_row(row, original_columns)
            if not normalized:
                continue
            dedup_key = self._dedup_key(normalized)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            cleaned.append(normalized)
        logger.info(
            f'Cleaner: {len(rows)} → {len(cleaned)} '
            f'({len(rows) - len(cleaned)} removed)'
        )
        return cleaned

    def _normalize_row(self, row, original_columns):
        normalized = {}
        has_content = False
        for col, val in row.items():
            if val is None:
                normalized[col] = ''
                continue
            val = str(val).strip()
            val = self._fix_encoding(val)
            val = self._normalize_text(val)
            normalized[col] = val
            if val:
                has_content = True
        if not has_content:
            return None
        name = self._extract_field(original_columns, normalized, 'name')
        if name:
            return normalized
        return None

    def _extract_field(self, columns, row, field):
        keywords = FIELD_KEYWORDS.get(field, [])
        for col_name in columns:
            col_lower = unidecode(col_name.lower().strip())
            for kw in keywords:
                if kw in col_lower:
                    val = row.get(col_name, '')
                    if val and str(val).strip():
                        return str(val).strip()
        return ''

    def _fix_encoding(self, text):
        try:
            text.encode('latin-1')
            try:
                text.encode('utf-8')
            except UnicodeEncodeError:
                text = text.encode('latin-1').decode('utf-8', errors='replace')
        except (UnicodeEncodeError, UnicodeDecodeError):
            text = text.encode('utf-8', errors='replace').decode('utf-8')
        return text

    def _normalize_text(self, text):
        text = text.lower().strip()
        text = unidecode(text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _dedup_key(self, row):
        combined = '|'.join(
            str(v) for v in row.values() if v
        )
        return combined

    @staticmethod
    def normalize_company_text(name, description=''):
        combined = f'{name} {description}'.lower().strip()
        combined = unidecode(combined)
        combined = re.sub(r'[^\w\s]', ' ', combined)
        combined = re.sub(r'\s+', ' ', combined).strip()
        return combined
