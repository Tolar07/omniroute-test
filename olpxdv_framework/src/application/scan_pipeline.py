"""
Scan Pipeline - Data ingestion and engine consensus generation.

This module implements the SCAN phase of the OLP XDV pipeline:
1. Ingest fixture data from external APIs
2. Ingest odds data from bookmakers
3. Generate engine consensus predictions
4. Prepare data for trigger phase
"""

from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ...domain.models import (
    Fixture, Odds, EngineConsensus, MarketType,
    FixtureRepository, OddsRepository
)
from ...domain.protected_constants import (
    get_current_phase, is_paper_only, all_fixtures_eligible,
    get_whitelisted_leagues
)
from ...domain.knowledge_persistence import KnowledgeItem, KnowledgeRepository
from ...domain.engine_suite import EngineSuite
from ...infrastructure.api_adapters import (
    TheOddsAPIAdapter, APIFootballAdapter, TheSportsDBAdapter
)
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


class ScanPipeline:
    """
    Implements the SCAN phase: data ingestion and engine consensus.

    Responsibilities:
    - Fetch upcoming fixtures from sports APIs
    - Fetch latest odds for those fixtures
    - Run engine suite to generate consensus predictions
    - Persist fixtures, odds, and consensus to repositories
    - Generate knowledge items for audit trail
    """

    def __init__(
        self,
        fixture_repo: FixtureRepository,
        odds_repo: OddsRepository,
        knowledge_repo: Optional[KnowledgeRepository] = None
    ):
        self.fixture_repo = fixture_repo
        self.odds_repo = odds_repo
        self.knowledge_repo = knowledge_repo
        self.engine_suite = EngineSuite()
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize API adapters
        self.odds_apis = [
            TheOddsAPIAdapter(),
            APIFootballAdapter(),
            TheSportsDBAdapter()
        ]

    async def run_scan_cycle(self) -> Dict[str, Any]:
        """
        Execute a complete scan cycle.

        Returns:
            Dictionary with scan results and metadata
        """
        scan_start = datetime.utcnow()
        self.logger.info("Starting scan cycle")

        try:
            # Step 1: Fetch upcoming fixtures
            fixtures = await self._fetch_upcoming_fixtures()
            self.logger.info(f"Fetched {len(fixtures)} upcoming fixtures")

            # Step 2: Persist fixtures
            persisted_fixtures = await self._persist_fixtures(fixtures)

            # Step 3: Fetch odds for fixtures
            odds_map = await self._fetch_odds_for_fixtures(persisted_fixtures)

            # Step 4: Persist odds
            persisted_odds = await self._persist_odds(odds_map)

            # Step 5: Generate engine consensus
            consensus_list = await self._generate_engine_consensus(
                persisted_fixtures, persisted_odds
            )

            # Step 6: Persist consensus (if repository supports it)
            # Note: Consensus might be ephemeral or stored elsewhere

            # Step 7: Generate knowledge items for audit
            if self.knowledge_repo:
                await self._generate_scan_knowledge(
                    fixtures, odds_map, consensus_list, scan_start
                )

            scan_end = datetime.utcnow()
            duration = (scan_end - scan_start).total_seconds()

            result = {
                "status": "success",
                "fixtures_processed": len(persisted_fixtures),
                "odds_records": len(persisted_odds),
                "consensus_generated": len(consensus_list),
                "duration_seconds": duration,
                "timestamp": scan_end.isoformat(),
                "phase": self.settings.framework.current_phase
            }

            self.logger.info(f"Scan cycle completed in {duration:.2f}s: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Scan cycle failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _fetch_upcoming_fixtures(self) -> List[Fixture]:
        """
        Fetch upcoming fixtures from all available sports APIs.
        """
        all_fixtures = []

        # Try each API adapter until we get data
        for adapter in self.odds_apis:
            try:
                fixtures = await adapter.get_upcoming_fixtures(
                    days_ahead=7,  # Look ahead 7 days
                    leagues=self._get_eligible_leagues()
                )
                if fixtures:
                    all_fixtures.extend(fixtures)
                    self.logger.info(f"Got {len(fixtures)} fixtures from {adapter.__class__.__name__}")
                    break  # Use first successful source
            except Exception as e:
                self.logger.warning(f"Failed to fetch fixtures from {adapter.__class__.__name__}: {e}")
                continue

        # Deduplicate by fixture ID
        seen_ids = set()
        unique_fixtures = []
        for fixture in all_fixtures:
            if fixture.id not in seen_ids:
                seen_ids.add(fixture.id)
                unique_fixtures.append(fixture)

        # Filter by eligibility
        eligible_fixtures = [
            f for f in unique_fixtures
            if self._is_fixture_eligible(f)
        ]

        self.logger.info(f"After filtering: {len(eligible_fixtures)} eligible fixtures")
        return eligible_fixtures

    def _get_eligible_leagues(self) -> List[str]:
        """Get list of leagues eligible for scanning."""
        if all_fixtures_eligible():
            return []  # Empty means all leagues
        return get_whitelisted_leagues()

    def _is_fixture_eligible(self, fixture: Fixture) -> bool:
        """Check if a fixture is eligible for scanning based on configuration."""
        # Phase-based eligibility
        current_phase = get_current_phase()
        if current_phase < 1:  # Phase 0 doesn't exist, but safety check
            return False

        # League eligibility
        if not all_fixtures_eligible():
            whitelisted = set(get_whitelisted_leagues())
            if fixture.league not in whitelisted:
                return False

        # Date eligibility (not too far in past/future)
        now = datetime.utcnow()
        if fixture.match_date < now - timedelta(days=1):  # Not yesterday or earlier
            return False
        if fixture.match_date > now + timedelta(days=30):  # Not more than 30 days out
            return False

        # Status eligibility
        if fixture.status not in [FixtureStatus.SCHEDULED, FixtureStatus.LIVE]:
            return False

        return True

    async def _persist_fixtures(self, fixtures: List[Fixture]) -> List[Fixture]:
        """Persist fixtures to repository."""
        persisted = []
        for fixture in fixtures:
            try:
                persisted_fixture = await self.fixture_repo.save(fixture)
                persisted.append(persisted_fixture)
            except Exception as e:
                self.logger.error(f"Failed to persist fixture {fixture.id}: {e}")
        return persisted

    async def _fetch_odds_for_fixtures(self, fixtures: List[Fixture]) -> Dict[str, List[Odds]]:
        """
        Fetch odds for all fixtures from available APIs.
        Returns dictionary mapping fixture_id to list of odds.
        """
        odds_map = {}

        # Process fixtures in batches to avoid overwhelming APIs
        batch_size = 10
        for i in range(0, len(fixtures), batch_size):
            batch = fixtures[i:i + batch_size]
            batch_tasks = [
                self._fetch_odds_for_fixture(fixture)
                for fixture in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for fixture, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to fetch odds for fixture {fixture.id}: {result}")
                    odds_map[fixture.id] = []
                else:
                    odds_map[fixture.id] = result

            # Small delay between batches to be respectful to APIs
            if i + batch_size < len(fixtures):
                await asyncio.sleep(1)

        return odds_map

    async def _fetch_odds_for_fixture(self, fixture: Fixture) -> List[Odds]:
        """Fetch odds for a single fixture from available APIs."""
        all_odds = []

        # Try each API adapter
        for adapter in self.odds_apis:
            try:
                odds = await adapter.get_odds_for_fixture(
                    fixture.id,
                    market_types=[MarketType.MATCH_ODDS, MarketType.OVER_UNDER, MarketType.BTTS]
                )
                if odds:
                    all_odds.extend(odds)
                    # If we got odds from this source, we might not need others
                    # but we'll collect from all for redundancy
            except Exception as e:
                self.logger.warning(f"Failed to fetch odds from {adapter.__class__.__name__} for {fixture.id}: {e}")
                continue

        # Deduplicate odds by (fixture_id, market_type, selection, bookmaker)
        seen = set()
        unique_odds = []
        for odds in all_odds:
            key = (odds.fixture_id, odds.market_type, odds.selection, odds.bookmaker)
            if key not in seen:
                seen.add(key)
                unique_odds.append(odds)

        return unique_odds

    async def _persist_odds(self, odds_map: Dict[str, List[Odds]]) -> List[Odds]:
        """Persist odds to repository."""
        persisted = []
        for fixture_id, odds_list in odds_map.items():
            for odds in odds_list:
                try:
                    persisted_odds = await self.odds_repo.save(odds)
                    persisted.append(persisted_odds)
                except Exception as e:
                    self.logger.error(f"Failed to persist odds {odds.id}: {e}")
        return persisted

    async def _generate_engine_consensus(
        self,
        fixtures: List[Fixture],
        odds_map: Dict[str, List[Odds]]
    ) -> List[EngineConsensus]:
        """
        Generate engine consensus predictions for fixtures with odds.
        """
        consensus_list = []

        for fixture in fixtures:
            fixture_odds = odds_map.get(fixture.id, [])
            if not fixture_odds:
                self.logger.warning(f"No odds available for fixture {fixture.id}")
                continue

            try:
                consensus = await self.engine_suite.generate_consensus(
                    fixture, fixture_odds
                )
                if consensus:
                    consensus_list.append(consensus)
            except Exception as e:
                self.logger.error(f"Failed to generate consensus for fixture {fixture.id}: {e}")
                continue

        return consensus_list

    async def _generate_scan_knowledge(
        self,
        fixtures: List[Fixture],
        odds_map: Dict[str, List[Odds]],
        consensus_list: List[EngineConsensus],
        scan_start: datetime
    ) -> None:
        """Generate knowledge items for scan cycle audit trail."""
        if not self.knowledge_repo:
            return

        try:
            # Create summary knowledge item
            summary_content = f"""Scan Cycle Completed:
- Timestamp: {scan_start.isoformat()}
- Fixtures processed: {len(fixtures)}
- Odds records: {sum(len(odds) for odds in odds_map.values())}
- Consensus generated: {len(consensus_list)}
- Current phase: {get_current_phase()}
- Paper only mode: {is_paper_only()}
"""

            knowledge_item = KnowledgeItem(
                id=f"scan-{scan_start.strftime('%Y%m%d-%H%M%S')}",
                title=f"Scan Cycle - {scan_start.strftime('%Y-%m-%d %H:%M:%S')}",
                content=summary_content,
                knowledge_type="process",
                source="scan_pipeline",
                tags=["scan", "pipeline", "data-ingestion"],
                relevance_score=Decimal('0.8'),
                confidence=Decimal('0.95'),
                created_at=scan_start,
                updated_at=scan_start
            )

            await self.knowledge_repo.save(knowledge_item)
            self.logger.debug("Saved scan cycle knowledge item")

        except Exception as e:
            self.logger.error(f"Failed to generate scan knowledge: {e}")


# Factory function for easy instantiation
def create_scan_pipeline(
    fixture_repo: FixtureRepository,
    odds_repo: OddsRepository,
    knowledge_repo: Optional[KnowledgeRepository] = None
) -> ScanPipeline:
    """Factory function to create a ScanPipeline instance."""
    return ScanPipeline(fixture_repo, odds_repo, knowledge_repo)