import logging
import re

import bleach
from django.template import Template, Context
from django.template.exceptions import TemplateSyntaxError

logger = logging.getLogger(__name__)

ALLOWED_TAGS = [
    'html', 'head', 'body', 'meta', 'title',
    'p', 'br', 'b', 'i', 'u', 'em', 'strong', 'a', 'span', 'div',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'img', 'hr', 'blockquote', 'pre', 'code',
    'style', 'font', 'center',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'target', 'rel', 'style'],
    'img': ['src', 'alt', 'width', 'height', 'style', 'loading', 'srcset', 'align', 'border'],
    'span': ['style'],
    'div': ['style'],
    'p': ['style'],
    'td': ['style', 'colspan', 'rowspan', 'align', 'valign', 'bgcolor'],
    'th': ['style', 'colspan', 'rowspan', 'align', 'valign', 'bgcolor'],
    'tr': ['style', 'bgcolor', 'align', 'valign'],
    'table': ['style', 'border', 'cellpadding', 'cellspacing', 'bgcolor', 'width', 'align'],
    'body': ['style', 'bgcolor'],
    'font': ['style', 'color', 'size', 'face'],
    'style': ['type'],
    'meta': ['charset', 'name', 'content'],
}


def _detect_variables(html):
    pattern = re.compile(r'\{\{\s*(\w+(?:\.\w+)*)\s*\}\}')
    return set(pattern.findall(html))


def validate_variables(html, allowed_vars):
    used = _detect_variables(html)
    missing = used - set(allowed_vars)
    if missing:
        logger.warning(f'Variables no definidas en plantilla: {missing}')
    return missing


def render_template(template_obj, context):
    if not isinstance(context, dict):
        raise TypeError('context debe ser un diccionario')

    html = template_obj.body_html
    subject = template_obj.subject

    sanitized_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )

    missing = validate_variables(sanitized_html, template_obj.variables)
    safe_context = {k: str(v) if v is not None else '' for k, v in context.items()}

    missing_in_context = [v for v in _detect_variables(sanitized_html) if v not in safe_context]
    if missing_in_context:
        logger.warning(f'Variables sin valor en context: {missing_in_context}')
        for var in missing_in_context:
            safe_context[var] = ''

    try:
        django_template = Template(sanitized_html)
        rendered_html = django_template.render(Context(safe_context))

        django_subject = Template(subject)
        rendered_subject = django_subject.render(Context(safe_context))
    except TemplateSyntaxError as e:
        logger.error(f'Error al renderizar plantilla: {e}')
        raise

    return {
        'subject': rendered_subject,
        'body_html': rendered_html,
    }
