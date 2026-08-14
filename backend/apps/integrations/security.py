import hashlib
import hmac
import time
from functools import wraps

from django.conf import settings
from rest_framework.response import Response


def _secret():
    return getattr(settings, 'ALCRET_HMAC_SECRET', '')


def compute_signature(secret, body):
    """Calcula la firma HMAC-SHA256 sobre los bytes crudos del body."""
    return hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256,
    ).hexdigest()


def _is_timestamp_valid(timestamp, tolerance_seconds):
    if not timestamp:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    return abs(int(time.time()) - ts) <= tolerance_seconds


def require_alcret_signature(view_func):
    """Valida los headers X-Signature y X-Timestamp de un webhook de ALCRET.

    La firma es HMAC-SHA256 de los bytes crudos del body usando
    ALCRET_HMAC_SECRET. La comparación se hace con hmac.compare_digest
    para mitigar ataques de tiempo. X-Timestamp se valida como ventana
    de frescura (anti-replay) configurable con ALCRET_HMAC_TOLERANCE.
    """

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        secret = _secret()
        if not secret:
            return Response(
                {'error': 'ALCRET_HMAC_SECRET no configurado en el servidor'},
                status=403,
            )

        signature = request.META.get('HTTP_X_SIGNATURE', '')
        timestamp = request.META.get('HTTP_X_TIMESTAMP', '')
        if not signature or not timestamp:
            return Response(
                {'error': 'Headers X-Signature y X-Timestamp requeridos'},
                status=403,
            )

        tolerance = int(getattr(settings, 'ALCRET_HMAC_TOLERANCE', 900))
        if tolerance > 0 and not _is_timestamp_valid(timestamp, tolerance):
            return Response(
                {'error': 'X-Timestamp fuera de la ventana permitida'},
                status=403,
            )

        expected = compute_signature(secret, request.body)
        if not hmac.compare_digest(signature, expected):
            return Response(
                {'error': 'Firma HMAC inválida'},
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return wrapped
