import logging

from rest_framework.views import exception_handler
from django.conf import settings

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        if not settings.DEBUG:
            safe_data = {'detail': 'Ocurrió un error en el servidor.'}
            if isinstance(response.data, dict):
                if 'detail' in response.data:
                    safe_data['detail'] = response.data['detail']
            response.data = safe_data
    else:
        logger.error(f'Unhandled exception: {exc}', exc_info=True)
    return response
