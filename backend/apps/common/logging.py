import re
import logging


class ApiKeyRedactionFilter(logging.Filter):
    API_KEY_PATTERN = re.compile(r'(sk-[a-zA-Z0-9]{20,})|(pk-[a-zA-Z0-9]{20,})|(whsec_[a-zA-Z0-9]{32,})')

    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.API_KEY_PATTERN.sub('***REDACTED***', record.msg)
        if hasattr(record, 'args') and record.args:
            sanitized = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized.append(self.API_KEY_PATTERN.sub('***REDACTED***', arg))
                else:
                    sanitized.append(arg)
            record.args = tuple(sanitized)
        return True
