import re
from typing import Any

SECRET_PATTERNS = [
    # Query param or key=value style: access_token=EAAB...
    (
        re.compile(
            r"""(access_token|refresh_token|client_secret|signing_secret|page_access_token|secret|password)=[^&\s"']+""",
            re.IGNORECASE,
        ),
        r"\1=[REDACTED]",
    ),
    # JSON or dict style: "access_token": "EAAB..."
    (
        re.compile(
            r"""(["']?(?:access_token|refresh_token|client_secret|signing_secret|page_access_token|secret|password)["']?\s*:\s*["']?)[^"'\s,&}]+(["']?)""",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\2",
    ),
    # Bearer token style: Bearer EAAB...
    (
        re.compile(r"""(Bearer\s+)[A-Za-z0-9\-\._~\+\/]+=*""", re.IGNORECASE),
        r"\1[REDACTED]",
    ),
]


def sanitize_sensitive_data(text: Any) -> str:
    """
    Sanitizes sensitive values (tokens, secrets, credentials) from string representations.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
