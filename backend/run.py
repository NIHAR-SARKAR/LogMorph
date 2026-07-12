"""LogMorph backend launcher.

Reads SSL config from .env and starts uvicorn with both key + cert when present.

Usage:
    python run.py
    # or with explicit env file:
    ENV_FILE=.env python run.py

SSL env vars (set both to enable HTTPS):
    SSL_KEY_FILE=C:/path/to/key.key
    SSL_CERT_FILE=C:/path/to/cert.crt
"""

import uvicorn
from app.config import get_settings
from app.core.logging import logger


def main() -> None:
    settings = get_settings()
    ssl_params = settings.ssl_params

    if ssl_params:
        logger.info(
            "Starting HTTPS server on %s:%d (cert=%s, key=%s)",
            settings.BACKEND_HOST,
            settings.BACKEND_PORT,
            settings.SSL_CERT_FILE,
            settings.SSL_KEY_FILE,
        )
    else:
        logger.info(
            "Starting HTTP server on %s:%d (SSL not configured — set both SSL_KEY_FILE and SSL_CERT_FILE in .env to enable HTTPS)",
            settings.BACKEND_HOST,
            settings.BACKEND_PORT,
        )

    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
        **ssl_params,
    )


if __name__ == "__main__":
    main()
