#!/usr/bin/env python3
"""Development server runner for BildupAI Chat Service."""

import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
