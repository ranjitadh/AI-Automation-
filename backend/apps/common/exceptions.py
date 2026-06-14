from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        errors = response.data
        response.data = {
            'error': True,
            'detail': str(exc) if hasattr(exc, 'detail') else str(exc),
            'errors': errors,
            'status_code': response.status_code,
        }
    return response
