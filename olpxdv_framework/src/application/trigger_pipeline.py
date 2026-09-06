"""
Trigger Pipeline - Market selection and trigger logic.

This module implements the TRIGGER phase of the OLP XDV pipeline:
1. Evaluates engine consensus from scan phase
2. Applies triggering logic (value betting, Kelly criterion, etc.)
3. Creates CLV legs for approved bets
4. Prepares data for publish phase
"""

from __future__ import annotations
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from ...domain.models import (
    Fixture, Odds, EngineConsensus, CLVLeg, MarketType, BetResult,
    FixtureRepository, OddsRepository, CLVLegRepository
)
from ...domain.protected_constants import (
    get_current_phase, is_paper_only, is_client_publish_enabled,
    get_max_kelly_fraction, get_min_mes_floor, get_whitelisted_leagues,
    all_fixtures_eligible, is_fabrication_detection_enabled
)
from ...domain.clv_calculator import CLVCalculator
from ...domain.fabrication_detector import FabricationDetector
from ...domain.knowledge_persistence import KnowledgeItem, KnowledgeRepository
from ...config.settings import get_settings

logger = logging.getLogger(__name__)


class TriggerPipeline:
    """
    Implements the TRIGGER phase: market selection and trigger logic.

    Responsibilities:
    - Evaluate engine consensus for betting opportunities
    - Apply value betting and Kelly criterion logic
    - Perform fabrication detection on data
    - Create CLV legs for approved bets (paper or live)
    - Apply risk management and position sizing
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
        self.fabrication_detector = FabricationDetector()
        self.settings = get_settings()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run_trigger_cycle(
        self,
        consensus_list: List[EngineConsensus]
    ) -> Dict[str, Any]:
        """
        Execute a complete trigger cycle.

        Args:
            consensus_list: List of engine consensus from scan phase

        Returns:
            Dictionary with trigger results and metadata
        """
        trigger_start = datetime.utcnow()
        self.logger.info(f"Starting trigger cycle with {len(consensus_list)} consensus items")

        try:
            # Step 1: Filter consensus by eligibility and phase
            eligible_consensus = await self._filter_eligible_consensus(consensus_list)
            self.logger.info(f"After eligibility filtering: {len(eligible_consensus)} consensus items")

            # Step 2: Apply fabrication detection
            clean_consensus = await self._apply_fabrication_detection(eligible_consensus)
            self.logger.info(f"After fabrication detection: {len(clean_consensus)} consensus items")

            # Step 3: Calculate betting recommendations
            betting_recommendations = await self._calculate_betting_recommendations(clean_consensus)
            self.logger.info(f"Generated {len(betting_recommendations)} betting recommendations")

            # Step 4: Apply risk management and position sizing
            risk_adjusted_recommendations = await self._apply_risk_management(betting_recommendations)
            self.logger.info(f"After risk management: {len(risk_adjusted_recommendations)} recommendations")

            # Step 5: Create CLV legs for approved bets
            created_legs = await self._create_clv_legs(risk_adjusted_recommendations)
            self.logger.info(f"Created {len(created_legs)} CLV legs")

            # Step 6: Generate knowledge items for audit
            if self.knowledge_repo:
                await self._generate_trigger_knowledge(
                    consensus_list, eligible_consensus, clean_consensus,
                    betting_recommendations, risk_adjusted_recommendations,
                    created_legs, trigger_start
                )

            trigger_end = datetime.utcnow()
            duration = (trigger_end - trigger_start).total_seconds()

            result = {
                "status": "success",
                "input_consensus": len(consensus_list),
                "eligible_consensus": len(eligible_consensus),
                "clean_consensus": len(clean_consensus),
                "betting_recommendations": len(betting_recommendations),
                "risk_adjusted": len(risk_adjusted_recommendations),
                "clv_legs_created": len(created_legs),
                "duration_seconds": duration,
                "timestamp": trigger_end.isoformat(),
                "phase": self.settings.framework.current_phase
            }

            self.logger.info(f"Trigger cycle completed in {duration:.2f}s: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Trigger cycle failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def _filter_eligible_consensus(
        self,
        consensus_list: List[EngineConsensus]
    ) -> List[EngineConsensus]:
        """
        Filter consensus items based on eligibility criteria.
        """
        eligible = []

        for consensus in consensus_list:
            try:
                # Get fixture to check eligibility
                fixture = await self.fixture_repo.get_by_id(consensus.fixture_id)
                if not fixture:
                    self.logger.warning(f"Fixture not found for consensus {consensus.fixture_id}")
                    continue

                # Check fixture eligibility (similar to scan pipeline)
                if not self._is_fixture_eligible(fixture):
                    continue

                # Check phase eligibility
                current_phase = get_current_phase()
                if current_phase < 1:  # Phase 0 doesn't exist
                    continue

                # Check probability thresholds
                if consensus.probability < Decimal('0.1') or consensus.probability > Decimal('0.9'):
                    # Too extreme probabilities might indicate data issues
                    continue

                # Check confidence threshold
                if consensus.confidence < Decimal('0.5'):
                    continue

                eligible.append(consensus)

            except Exception as e:
                self.logger.error(f"Error filtering consensus {consensus.fixture_id}: {e}")
                continue

        return eligible

    def _is_fixture_eligible(self, fixture: Fixture) -> bool:
        """Check if a fixture is eligible for triggering (same logic as scan)."""
        # League eligibility
        if not all_fixtures_eligible():
            whitelisted = set(get_whitelisted_leagues())
            if fixture.league not in whitelisted:
                return False

        # Date eligibility
        now = datetime.utcnow()
        if fixture.match_date < now - timedelta(days=1):
            return False
        if fixture.match_date > now + timedelta(days=30):
            return False

        # Status eligibility
        if fixture.status not in [FixtureStatus.SCHEDULED, FixtureStatus.LIVE]:
            return False

        return True

    async def _apply_fabrication_detection(
        self,
        consensus_list: List[EngineConsensus]
    ) -> List[EngineConsensus]:
        """
        Apply fabrication detection to filter out potentially fabricated data.
        """
        if not is_fabrication_detection_enabled():
            return consensus_list

        clean_consensus = []

        for consensus in consensus_list:
            try:
                # Get fixture and odds for analysis
                fixture = await self.fixture_repo.get_by_id(consensus.fixture_id)
                if not fixture:
                    continue

                odds_list = await self.odds_repo.get_by_fixture_and_market(
                    consensus.fixture_id, consensus.market_type
                )

                # Check for fabrication patterns
                is_fabricated, reason = await self.fabrication_detector.detect_fabrication(
                    fixture, odds_list, consensus
                )

                if not is_fabricated:
                    clean_consensus.append(consensus)
                else:
                    self.logger.warning(
                        f"Filtered fabricated consensus {consensus.fixture_id}: {reason}"
                    )

                    # Generate knowledge item for fabrication detection
                    if self.knowledge_repo:
                        await self._log_fabrication_event(
                            fixture, consensus, reason
                        )

            except Exception as e:
                self.logger.error(f"Error in fabrication detection for {consensus.fixture_id}: {e}")
                # In case of error, err on the side of caution and exclude
                continue

        return clean_consensus

    async def _calculate_betting_recommendations(
        self,
        consensus_list: List[EngineConsensus]
    ) -> List[Dict[str, Any]]:
        """
        Calculate betting recommendations from clean consensus.
        """
        recommendations = []

        for consensus in consensus_list:
            try:
                # Get latest odds for this consensus
                odds_list = await self.odds_repo.get_latest(
                    consensus.fixture_id, consensus.market_type
                )

                if not odds_list:
                    self.logger.warning(f"No odds found for {consensus.fixture_id} {consensus.market_type}")
                    continue

                # Use the best available odds (highest for positive EV)
                best_odds = max(odds_list, key=lambda o: o.decimal_odds)

                # Calculate expected value
                expected_value = self.clv_calculator.calculate_expected_value(
                    consensus.probability, best_odds.decimal_odds
                )

                # Only consider positive EV bets
                if expected_value <= Decimal('0'):
                    continue

                # Check minimum edge requirement
                min_edge = get_min_mes_floor()
                edge = float(expected_value)  # For unit stake, EV = edge
                if edge < float(min_edge):
                    continue

                # Calculate Kelly fraction
                kelly_fraction = self.clv_calculator.calculate_kelly_fraction(
                    consensus.probability, best_odds.decimal_odds
                )

                # Calculate recommended stake (assuming unit bankroll for now)
                # In practice, bankroll would come from portfolio management
                recommended_stake = self.clv_calculator.calculate_recommended_stake(
                    consensus.probability, best_odds.decimal_odds,
                    bankroll=Decimal('1000.0'),  # Placeholder bankroll
                    use_kelly=True
                )

                recommendation = {
                    "consensus": consensus,
                    "fixture_id": consensus.fixture_id,
                    "market_type": consensus.market_type,
                    "selection": consensus.selection,
                    "probability": consensus.probability,
                    "confidence": consensus.confidence,
                    "decimal_odds": best_odds.decimal_odds,
                    "expected_value": expected_value,
                    "edge": Decimal(str(edge)),
                    "kelly_fraction": kelly_fraction,
                    "recommended_stake": recommended_stake,
                    "odds_id": best_odds.id,
                    "timestamp": datetime.utcnow()
                }

                recommendations.append(recommendation)

            except Exception as e:
                self.logger.error(f"Error calculating recommendation for {consensus.fixture_id}: {e}")
                continue

        # Sort by expected value descending
        recommendations.sort(key=lambda x: x["expected_value"], reverse=True)

        return recommendations

    async def _apply_risk_management(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply risk management rules to betting recommendations.
        """
        if not recommendations:
            return recommendations

        risk_adjusted = []
        daily_exposure = Decimal('0')
        max_daily_exposure = get_max_kelly_fraction() * Decimal('1000.0')  # Assuming 1000 unit bankroll

        for rec in recommendations:
            try:
                # Check daily exposure limit
                if daily_exposure >= max_daily_exposure:
                    self.logger.warning(f"Daily exposure limit reached: {daily_exposure}")
                    break

                stake = rec["recommended_stake"]

                # Check single bet exposure limit
                max_single_bet = get_max_kelly_fraction() * Decimal('1000.0')  # Simplified
                if stake > max_single_bet:
                    stake = max_single_bet
                    rec["recommended_stake"] = stake
                    rec["note"] = f"Stake capped to max single bet: {max_single_bet}"

                # Check if adding this bet would exceed daily limit
                if daily_exposure + stake > max_daily_exposure:
                    # Scale down stake to fit remaining daily exposure
                    remaining = max_daily_exposure - daily_exposure
                    if remaining > Decimal('0'):
                        stake = remaining
                        rec["recommended_stake"] = stake
                        rec["note"] = f"Stake scaled to fit daily limit: {stake}"
                    else:
                        continue  # No room left

                daily_exposure += stake
                risk_adjusted.append(rec)

            except Exception as e:
                self.logger.error(f"Error applying risk management: {e}")
                continue

        return risk_adjusted

    async def _create_clv_legs(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> List[CLVLeg]:
        """
        Create CLV legs for approved betting recommendations.
        """
        created_legs = []

        for rec in recommendations:
            try:
                # Only create legs if we're in a phase that allows betting
                current_phase = get_current_phase()
                if current_phase < 1:  # Phase 0 doesn't exist
                    continue

                # In paper-only mode, we still create legs for tracking
                # In live phases, we might actually place bets (but this framework focuses on paper tracking)
                is_paper = is_paper_only()

                # Create CLV leg
                leg = self.clv_calculator.log_clv_leg(
                    fixture_id=rec["fixture_id"],
                    market_type=rec["market_type"],
                    selection=rec["selection"],
                    opening_odds=rec["decimal_odds"],
                    stake=rec["recommended_stake"]
                )

                # Additional metadata could be stored in leg extensions or separate tables
                # For now, we'll log the recommendation details

                self.logger.info(
                    f"Created CLV leg {leg.id}: {rec['fixture_id']} {rec['market_type'].value} "
                    f"{rec['selection']} @ {rec['decimal_odds']} (stake: {rec['recommended_stake']}, "
                    f"EV: {rec['expected_value']:.4f})"
                )

                created_legs.append(leg)

                # Persist the leg to repository
                await self.clv_leg_repo.save(leg)

            except Exception as e:
                self.logger.error(f"Error creating CLV leg for {rec.get('fixture_id', 'unknown')}: {e}")
                continue

        return created_legs

    async def _generate_trigger_knowledge(
        self,
        input_consensus: List[EngineConsensus],
        eligible_consensus: List[EngineConsensus],
        clean_consensus: List[EngineConsensus],
        betting_recommendations: List[Dict[str, Any]],
        risk_adjusted: List[Dict[str, Any]],
        created_legs: List[CLVLeg],
        trigger_start: datetime
    ) -> None:
        """Generate knowledge items for trigger cycle audit trail."""
        if not self.knowledge_repo:
            return

        try:
            # Create summary knowledge item
            summary_content = f"""Trigger Cycle Completed:
- Timestamp: {trigger_start.isoformat()}
- Input consensus: {len(input_consensus)}
- Eligible consensus: {len(eligible_consensus)}
- After fabrication detection: {len(clean_consensus)}
- Betting recommendations: {len(betting_recommendations)}
- After risk management: {len(risk_adjusted)}
- CLV legs created: {len(created_legs)}
- Current phase: {get_current_phase()}
- Paper only mode: {is_paper_only()}
- Client publishing enabled: {is_client_publish_enabled()}
"""

            # Add details of top recommendations
            if betting_recommendations:
                summary_content += "\nTop 5 Recommendations:\n"
                for i, rec in enumerate(betting_recommendations[:5]):
                    summary_content += (
                        f"{i+1}. {rec['fixture_id']} {rec['market_type'].value} {rec['selection']} "
                        f"@ {rec['decimal_odds']} (P={rec['probability']:.3f}, "
                        f"EV={rec['expected_value']:.4f}, stake={rec['recommended_stake']})\n"
                    )

            knowledge_item = KnowledgeItem(
                id=f"trigger-{trigger_start.strftime('%Y%m%d-%H%M%S')}",
                title=f"Trigger Cycle - {trigger_start.strftime('%Y-%m-%d %H:%M:%S')}",
                content=summary_content,
                knowledge_type="process",
                source="trigger_pipeline",
                tags=["trigger", "pipeline", "betting", "recommendations"],
                relevance_score=Decimal('0.85'),
                confidence=Decimal('0.95'),
                created_at=trigger_start,
                updated_at=trigger_start
            )

            await self.knowledge_repo.save(knowledge_item)
            self.logger.debug("Saved trigger cycle knowledge item")

        except Exception as e:
            self.logger.error(f"Failed to generate trigger knowledge: {e}")

    async def _log_fabrication_event(
        self,
        fixture: Fixture,
        consensus: EngineConsensus,
        reason: str
    ) -> None:
        """Log a fabrication detection event as knowledge."""
        if not self.knowledge_repo:
            return

        try:
            knowledge_item = KnowledgeItem(
                id=f"fabrication-{fixture.id}-{consensus.market_type.value}-{int(datetime.utcnow().timestamp())}",
                title=f"Fabrication Detection: {fixture.id}",
                content=f"""Fabrication Detection Triggered:
- Fixture: {fixture.id} ({fixture.home_team.name} vs {fixture.away_team.name})
- Market: {consensus.market_type.value}
- Selection: {consensus.selection}
- Probability: {consensus.probability}
- Reason: {reason}
- Timestamp: {datetime.utcnow().isoformat()}
""",
                knowledge_type="observation",
                source="fabrication_detector",
                tags=["fabrication", "detection", "data-quality"],
                relevance_score=Decimal('0.9'),
                confidence=Decimal('0.9'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            await self.knowledge_repo.save(knowledge_item)
            self.logger.debug("Saved fabrication detection knowledge item")

        except Exception as e:
            self.logger.error(f"Failed to log fabrication event: {e}")


# Factory function for easy instantiation
def create_trigger_pipeline(
    fixture_repo: FixtureRepository,
    odds_repo: OddsRepository,
    clv_leg_repo: CLVLegRepository,
    knowledge_repo: Optional[KnowledgeRepository] = None
) -> TriggerPipeline:
    """Factory function to create a TriggerPipeline instance."""
    return TriggerPipeline(fixture_repo, odds_repo, clv_leg_repo, knowledge_repo)