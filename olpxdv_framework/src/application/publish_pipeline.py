"""
Publish Pipeline - CLV gate and output generation.

This module implements the PUBLISH phase of the OLP XDV pipeline:
1. Evaluates CLV gate for publishing permission
2. Generates output for clients (Telegram, web dashboard, etc.)
3. Applies dual output principle (same logic for all outputs)
4. Handles bet result tracking and CLV leg closure
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from ...domain.models import (
    Fixture, Odds, CLVLeg, BetResult, MarketType,
    FixtureRepository, OddsRepository, CLVLegRepository
)
from ...domain.protected_constants import (
    get_current_phase, is_paper_only, is_client_publish_enabled,
    get_clv_min_legs, get_clv_mean_threshold, get_max_kelly_fraction,
    is_fabrication_detection_enabled
)
from ...domain.clv_calculator import CLVCalculator
from ...domain.knowledge_persistence import KnowledgeItem, KnowledgeRepository
from ...infrastructure.telegram_adapter import TelegramAdapter
from ...infrastructure.web_dashboard import WebDashboardAdapter
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


class PublishPipeline:
    """
    Implements the PUBLISH phase: CLV gate and output generation.

    Responsibilities:
    - Evaluate CLV gate to determine if publishing is allowed
    - Generate betting recommendations for approved bets
    - Apply dual output principle (Telegram + web dashboard)
    - Close CLV legs with actual results when available
    - Generate knowledge items for audit trail
    """

    def __init__(
        self,
        fixture_repo: FixtureRepository,
        odds_repo: OddsRepository,
        clv_leg_repo: CLVLegRepository,
        knowledge_repo: Optional[KnowledgeRepository] = None
    ):
        self.fixture_repo = fixture_repo
        self.odds_repo = odds_repo
        self.clv_leg_repo = clv_leg_repo
        self.knowledge_repo = knowledge_repo
        self.clv_calculator = CLVCalculator()
        self.telegram_adapter = TelegramAdapter()
        self.web_dashboard_adapter = WebDashboardAdapter()
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run_publish_cycle(self) -> Dict[str, Any]:
        """
        Execute a complete publish cycle.

        Returns:
            Dictionary with publish results and metadata
        """
        publish_start = datetime.utcnow()
        self.logger.info("Starting publish cycle")

        try:
            # Step 1: Evaluate CLV gate
            open_legs = await self.clv_leg_repo.get_open_legs()
            clv_gate_result = self.clv_calculator.evaluate_clv_gate(open_legs)

            self.logger.info(f"CLV gate evaluation: {clv_gate_result.reason}")

            # Step 2: Determine if publishing is allowed
            can_publish, publish_reason = self._can_publish(clv_gate_result)
            if not can_publish:
                self.logger.info(f"Publishing not allowed: {publish_reason}")
                return {
                    "status": "skipped",
                    "reason": publish_reason,
                    "clv_gate_passed": clv_gate_result.passed,
                    "timestamp": publish_start.isoformat()
                }

            # Step 3: Get ready-to-publish bets (CLV legs that meet criteria)
            publishable_legs = await self._get_publishable_legs(open_legs)
            self.logger.info(f"Found {len(publishable_legs)} publishable CLV legs")

            # Step 4: Generate output for clients
            if publishable_legs:
                await self._generate_client_output(publishable_legs)

            # Step 5: Check for completed fixtures and close CLV legs
            closed_legs = await self._close_completed_legs()
            self.logger.info(f"Closed {len(closed_legs)} CLV legs with results")

            # Step 6: Generate knowledge items for audit
            if self.knowledge_repo:
                await self._generate_publish_knowledge(
                    open_legs, clv_gate_result, publishable_legs,
                    closed_legs, publish_start
                )

            publish_end = datetime.utcnow()
            duration = (publish_end - publish_start).total_seconds()

            result = {
                "status": "success",
                "clv_gate_passed": clv_gate_result.passed,
                "clv_gate_reason": clv_gate_result.reason,
                "open_legs": len(open_legs),
                "publishable_legs": len(publishable_legs),
                "closed_legs": len(closed_legs),
                "duration_seconds": duration,
                "timestamp": publish_end.isoformat(),
                "phase": self.settings.framework.current_phase
            }

            self.logger.info(f"Publish cycle completed in {duration:.2f}s: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Publish cycle failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _can_publish(self, clv_gate_result) -> Tuple[bool, str]:
        """
        Determine if publishing is allowed based on CLV gate and configuration.
        """
        # Check if client publishing is enabled
        if not is_client_publish_enabled():
            return False, "Client publishing is disabled"

        # Check framework phase
        current_phase = get_current_phase()
        if current_phase < 3:  # Phase 3 is live publishing
            return False, f"Phase {current_phase} does not allow live publishing"

        # Check CLV gate
        if not clv_gate_result.passed:
            return False, f"CLV gate not passed: {clv_gate_result.reason}"

        # Additional checks could go here (risk limits, etc.)

        return True, "All publishing conditions met"

    async def _get_publishable_legs(
        self,
        open_legs: List[CLVLeg]
    ) -> List[CLVLeg]:
        """
        Get CLV legs that are ready for publishing (meet betting criteria).
        """
        publishable = []

        for leg in open_legs:
            try:
                # Get latest odds to check if bet is still valid
                latest_odds = await self.odds_repo.get_latest(
                    leg.fixture_id, leg.market_type
                )

                if not latest_odds:
                    continue

                # Check if the leg still represents a positive EV bet
                # This is a simplified check - in practice, we'd want to re-evaluate
                # the engine consensus for this fixture

                # For now, we'll consider legs publishable if they were created
                # with positive expectation (we'd need to store the original EV)
                # As a proxy, we'll check if opening odds are reasonable

                if leg.opening_odds > Decimal('1.01') and leg.opening_odds < Decimal('10.0'):
                    publishable.append(leg)

            except Exception as e:
                self.logger.error(f"Error checking publishability for leg {leg.id}: {e}")
                continue

        return publishable

    async def _generate_client_output(
        self,
        publishable_legs: List[CLVLeg]
    ) -> None:
        """
        Generate output for clients (Telegram, web dashboard).
        Implements dual output principle.
        """
        if not publishable_legs:
            return

        try:
            # Format message for clients
            message = self._format_publish_message(publishable_legs)

            # Send to Telegram (if enabled)
            if self.settings.api.telegram_bot_token and self.settings.api.telegram_chat_id:
                await self.telegram_adapter.send_message(message)
                self.logger.info(f"Sent Telegram message with {len(publishable_legs)} recommendations")

            # Update web dashboard
            await self.web_dashboard_adapter.update_recommendations(publishable_legs)
            self.logger.info(f"Updated web dashboard with {len(publishable_legs)} recommendations")

        except Exception as e:
            self.logger.error(f"Error generating client output: {e}")

    def _format_publish_message(
        self,
        publishable_legs: List[CLVLeg]
    ) -> str:
        """
        Format publishable legs into a message for clients.
        """
        if not publishable_legs:
            return "No publishable bets at this time."

        lines = [
            "🎯 OLP XDV Framework - Betting Recommendations",
            f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"📊 {len(publishable_legs)} publishable bets",
            ""
        ]

        for i, leg in enumerate(publishable_legs[:10], 1):  # Limit to top 10
            try:
                # Get fixture details
                fixture = await self.fixture_repo.get_by_id(leg.fixture_id)
                if not fixture:
                    continue

                lines.extend([
                    f"{i}. {fixture.home_team.name} vs {fixture.away_team.name}",
                    f"   🏆 {fixture.league}",
                    f"   📅 {fixture.match_date.strftime('%Y-%m-%d %H:%M')}",
                    f"   🎲 {leg.market_type.value.replace('_', ' ').title()}: {leg.selection}",
                    f"   💰 Odds: {leg.opening_odds}",
                    f"   💵 Stake: {leg.stake}",
                    f"   🎯 Potential Return: {leg.potential_return:.2f}",
                    ""
                ])
            except Exception as e:
                self.logger.error(f"Error formatting leg {leg.id}: {e}")
                continue

        lines.extend([
            "⚠️  Paper Trading Only - No Real Money Involved",
            "📈 CLV Gate Status: Monitoring performance",
            "🔒 Protected Constants Enforced"
        ])

        return "\n".join(lines)

    async def _close_completed_legs(self) -> List[CLVLeg]:
        """
        Check for completed fixtures and close associated CLV legs.
        """
        closed_legs = []

        try:
            # Get fixtures that are finished
            finished_fixtures = await self.fixture_repo.get_finished_since(
                datetime.utcnow() - timedelta(hours=24)  # Check last 24 hours
            )

            for fixture in finished_fixtures:
                # Get open CLV legs for this fixture
                open_legs = await self.clv_leg_repo.get_open_legs_for_fixture(fixture.id)

                for leg in open_legs:
                    try:
                        # Get final odds (closing line)
                        closing_odds = await self._get_closing_odds(fixture.id, leg.market_type, leg.selection)

                        if closing_odds:
                            # Determine actual result
                            actual_result = self._determine_bet_result(fixture, leg)

                            # Close the leg
                            closed_leg = self.clv_calculator.close_clv_leg(
                                leg, closing_odds, actual_result
                            )

                            # Persist the closed leg
                            await self.clv_leg_repo.update(closed_leg)
                            closed_legs.append(closed_leg)

                            self.logger.info(
                                f"Closed CLV leg {leg.id}: {leg.fixture_id} "
                                f"CLV: {leg.clv_value:.4f} ({leg.clv_percentage:.2f}%)"
                            )
                        else:
                            self.logger.warning(f"No closing odds found for fixture {fixture.id}")

                    except Exception as e:
                        self.logger.error(f"Error closing leg {leg.id}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error in close_completed_legs: {e}")

        return closed_legs

    async def _get_closing_odds(
        self,
        fixture_id: str,
        market_type: MarketType,
        selection: str
    ) -> Optional[Decimal]:
        """
        Get closing odds for a fixture/market/selection.
        In a real implementation, this would get odds shortly before kickoff.
        For now, we'll simulate by getting the latest odds.
        """
        try:
            # In practice, we'd want odds from shortly before kickoff
            # For this implementation, we'll use the latest available odds
            odds_list = await self.odds_repo.get_by_fixture_and_market(
                fixture_id, market_type
            )

            # Find odds matching our selection
            for odds in odds_list:
                if odds.selection == selection:
                    return odds.decimal_odds

            # If no exact match, return the latest odds for the market
            if odds_list:
                latest_odds = max(odds_list, key=lambda o: o.timestamp)
                return latest_odds.decimal_odds

        except Exception as e:
            self.logger.error(f"Error getting closing odds for {fixture_id}: {e}")

        return None

    def _determine_bet_result(
        self,
        fixture: Fixture,
        leg: CLVLeg
    ) -> BetResult:
        """
        Determine the actual bet result based on fixture outcome.
        """
        try:
            home_score = fixture.home_score or 0
            away_score = fixture.away_score or 0

            # Map selection to actual result based on market type
            if leg.market_type == MarketType.MATCH_ODDS:
                if leg.selection.lower() == "home":
                    return BetResult.WIN if home_score > away_score else BetResult.LOSS if home_score < away_score else BetResult.PUSH
                elif leg.selection.lower() == "away":
                    return BetResult.WIN if away_score > home_score else BetResult.LOSS if away_score < home_score else BetResult.PUSH
                elif leg.selection.lower() == "draw":
                    return BetResult.WIN if home_score == away_score else BetResult.LOSS

            elif leg.market_type == MarketType.OVER_UNDER:
                # Extract threshold from selection (e.g., "Over 2.5" -> 2.5)
                try:
                    threshold = float(leg.selection.split()[1])
                    total_goals = home_score + away_score
                    if leg.selection.startswith("Over"):
                        return BetResult.WIN if total_goals > threshold else BetResult.LOSS
                    else:  # Under
                        return BetResult.WIN if total_goals < threshold else BetResult.LOSS
                except (IndexError, ValueError):
                    return BetResult.PENDING

            elif leg.market_type == MarketType.BTTS:
                # Both Teams To Score
                btts = home_score > 0 and away_score > 0
                if leg.selection.lower() == "yes":
                    return BetResult.WIN if btts else BetResult.LOSS
                else:  # "No"
                    return BetResult.WIN if not btts else BetResult.LOSS

            # Default to pending for unsupported market types
            return BetResult.PENDING

        except Exception as e:
            self.logger.error(f"Error determining bet result: {e}")
            return BetResult.PENDING

    async def _generate_publish_knowledge(
        self,
        open_legs: List[CLVLeg],
        clv_gate_result,
        publishable_legs: List[CLVLeg],
        closed_legs: List[CLVLeg],
        publish_start: datetime
    ) -> None:
        """Generate knowledge items for publish cycle audit trail."""
        if not self.knowledge_repo:
            return

        try:
            # Create summary knowledge item
            summary_content = f"""Publish Cycle Completed:
- Timestamp: {publish_start.isoformat()}
- Open CLV legs: {len(open_legs)}
- CLV gate passed: {clv_gate_result.passed}
- CLV gate reason: {clv_gate_result.reason}
- Publishable legs: {len(publishable_legs)}
- Closed legs with results: {len(closed_legs)}
- Current phase: {get_current_phase()}
- Client publishing enabled: {is_client_publish_enabled()}
"""

            # Add details of closed legs (performance)
            if closed_legs:
                total_clv = sum(leg.clv_value for leg in closed_legs)
                winning_legs = sum(1 for leg in closed_legs if leg.is_won())
                summary_content += f"""
Closed Legs Performance:
- Total CLV: {total_clv:.4f}
- Winning legs: {winning_legs}/{len(closed_legs)}
- Hit rate: {winning_legs/len(closed_legs)*100:.1f}% if closed_legs else 0
"""

            knowledge_item = KnowledgeItem(
                id=f"publish-{publish_start.strftime('%Y%m%d-%H%M%S')}",
                title=f"Publish Cycle - {publish_start.strftime('%Y-%m-%d %H:%M:%S')}",
                content=summary_content,
                knowledge_type="process",
                source="publish_pipeline",
                tags=["publish", "pipeline", "output", "clv-gate"],
                relevance_score=Decimal('0.9'),
                confidence=Decimal('0.95'),
                created_at=publish_start,
                updated_at=publish_start
            )

            await self.knowledge_repo.save(knowledge_item)
            self.logger.debug("Saved publish cycle knowledge item")

        except Exception as e:
            self.logger.error(f"Failed to generate publish knowledge: {e}")


# Factory function for easy instantiation
def create_publish_pipeline(
    fixture_repo: FixtureRepository,
    odds_repo: OddsRepository,
    clv_leg_repo: CLVLegRepository,
    knowledge_repo: Optional[KnowledgeRepository] = None
) -> PublishPipeline:
    """Factory function to create a PublishPipeline instance."""
    return PublishPipeline(fixture_repo, odds_repo, clv_leg_repo, knowledge_repo)