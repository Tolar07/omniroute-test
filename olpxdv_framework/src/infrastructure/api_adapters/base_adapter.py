"""
Base adapter for sports data APIs.
Defines the common interface that all API adapters must implement.
"""

from __future__ import annotations
import abc
import logging
from typing import List, Optional
from datetime import datetime

from ...domain.models import Fixture, Odds, MarketType


class BaseAPIAdapter(abc.ABC):
    """
    Abstract base class for all sports data API adapters.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abc.abstractmethod
    async def get_upcoming_fixtures(
        self,
        days_ahead: int = 7,
        leagues: Optional[List[str]] = None
    ) -> List[Fixture]:
        """
        Get upcoming fixtures from the API.

        Args:
            days_ahead: Number of days to look ahead
            leagues: Optional list of leagues to filter by

        Returns:
            List of Fixture objects
        """
        pass

    @abc.abstractmethod
    async def get_odds_for_fixture(
        self,
        fixture_id: str,
        market_types: List[MarketType]
    ) -> List[Odds]:
        """
        Get odds for a specific fixture.

        Args:
            fixture_id: The fixture identifier
            market_types: List of market types to get odds for

        Returns:
            List of Odds objects
        """
        pass

    @abc.abstractmethod
    async def get_latest_odds(
        self,
        fixture_id: str,
        market_type: MarketType
    ) -> Optional[Odds]:
        """
        Get the latest odds for a fixture and market type.

        Args:
            fixture_id: The fixture identifier
            market_type: The market type

        Returns:
            Latest Odds object or None
        """
        pass

    async def health_check(self) -> bool:
        """
        Check if the API is accessible and healthy.
        Returns True if healthy, False otherwise.
        """
        try:
            # Try a simple request to verify connectivity
            await self.get_upcoming_fixtures(days_ahead=1)
            return True
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class RateLimitError(APIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class AuthenticationError(APIError):
    """Exception raised when API authentication fails."""
    pass


class DataNotFoundError(APIError):
    """Exception raised when requested data is not found."""
    pass