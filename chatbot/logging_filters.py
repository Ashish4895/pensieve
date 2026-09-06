import logging
from collections.abc import Mapping


def _redact_api_keys(value):
    if isinstance(value, Mapping):
        return {
            key: "[REDACTED]" if str(key).lower() == "x-api-key" else _redact_api_keys(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(_redact_api_keys(item) for item in value)
    if isinstance(value, list):
        return [_redact_api_keys(item) for item in value]
    return value


class RedactApiKeyFilter(logging.Filter):
    def filter(self, record):
        record.msg = _redact_api_keys(record.msg)
        record.args = _redact_api_keys(record.args)
        return True
