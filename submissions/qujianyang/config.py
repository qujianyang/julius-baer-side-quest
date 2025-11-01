"""
Configuration Management for Banking Client
Demonstrates modern configuration practices vs hardcoded values
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BankingConfig:
    """
    Configuration class for banking client

    Modern approach using dataclass and environment variables
    vs legacy hardcoded values
    """

    # API Configuration
    base_url: str = "http://localhost:8123"
    timeout: int = 30  # seconds

    # Authentication defaults
    default_username: str = "admin"
    default_password: str = "password"

    # Connection settings
    max_retries: int = 3
    retry_delay: int = 1  # seconds

    # Logging level
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> 'BankingConfig':
        """
        Create configuration from environment variables
        Falls back to defaults if not set

        Environment variables:
        - BANKING_API_URL: Base URL for the API
        - BANKING_API_TIMEOUT: Request timeout in seconds
        - BANKING_USERNAME: Default username
        - BANKING_PASSWORD: Default password
        - BANKING_LOG_LEVEL: Logging level

        Returns:
            BankingConfig instance
        """
        return cls(
            base_url=os.getenv('BANKING_API_URL', cls.base_url),
            timeout=int(os.getenv('BANKING_API_TIMEOUT', cls.timeout)),
            default_username=os.getenv('BANKING_USERNAME', cls.default_username),
            default_password=os.getenv('BANKING_PASSWORD', cls.default_password),
            log_level=os.getenv('BANKING_LOG_LEVEL', cls.log_level)
        )

    def validate(self) -> bool:
        """
        Validate configuration values

        Returns:
            True if configuration is valid
        """
        if not self.base_url:
            return False
        if self.timeout <= 0:
            return False
        if self.max_retries < 0:
            return False
        return True


# Default configuration instance
default_config = BankingConfig()
