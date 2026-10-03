#!/usr/bin/env python3
"""
Script to run the full OLP XDV pipeline and produce betting recommendations.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_full_pipeline():
    """Run the complete OLP XDV pipeline."""
    try:
        logger.info("Starting OLP XDV Full Pipeline Execution")

        # Import framework components
        from olpxdv_framework.main import OLPXDVApplication
        from olpxdv_framework.config.settings import get_settings
        from olpxdv_framework.domain.models import Fixture, Team, LeagueTier, FixtureStatus, MarketType

        # Initialize application
        app = OLPXDVApplication()
        settings = get_settings()

        logger.info(f"Framework Phase: {settings.framework.current_phase}")
        logger.info(f"CLV Min Legs: {settings.framework.clv_min_legs}")
        logger.info(f"Client Publishing Enabled: {settings.framework.client_publish_enabled}")

        # Create test fixture for demonstration
        home_team = Team(id="demo_home_001", name="Demo Home Team")
        away_team = Team(id="demo_away_001", name="Demo Away Team")

        fixture = Fixture(
            id="DEMO_FIXTURE_001",
            home_team=home_team,
            away_team=away_team,
            league="Demo League",
            league_tier=LeagueTier.TIER_A,
            match_date=datetime(2026, 9, 15, 15, 0),
            status=FixtureStatus.SCHEDULED
        )

        logger.info(f"Created demo fixture: {fixture.id}")

        # Run SCAN pipeline (will likely return empty due to no API keys, but let's see)
        logger.info("Running SCAN pipeline...")
        scan_results = await app.scan_pipeline.run_scan_cycle(
            look_ahead_days=2,
            leagues=["Demo League"],
            market_types=[MarketType.MATCH_ODDS]
        )

        logger.info(f"SCAN pipeline completed. Found {len(scan_results)} consensus items")

        # If no real data, create mock consensus for demonstration
        if not scan_results:
            logger.info("No real data found, creating mock consensus for demonstration...")
            from olpxdv_framework.domain.models import EngineConsensus

            mock_consensus = EngineConsensus(
                fixture_id=fixture.id,
                market_type=MarketType.MATCH_ODDS,
                selection="Home",
                probability=Decimal('0.65'),  # 65% chance of home win
                expected_value=Decimal('0.12'),  # Positive EV
                confidence=Decimal('0.8'),
                kelly_fraction=Decimal('0.08'),
                engines_used=["Dixon-Coles", "Elo", "xG"],
                timestamp=datetime.utcnow()
            )
            scan_results = [mock_consensus]
            logger.info(f"Created {len(scan_results)} mock consensus items")

        # Run TRIGGER pipeline
        logger.info("Running TRIGGER pipeline...")
        trigger_results = await app.trigger_pipeline.run_trigger_cycle(scan_results)
        logger.info(f"TRIGGER pipeline completed. Found {len(trigger_results)} value bets")

        # Run PUBLISH pipeline
        logger.info("Running PUBLISH pipeline...")
        publish_results = await app.publish_pipeline.run_publish_cycle(trigger_results)
        logger.info(f"PUBLISH pipeline completed. Generated {len(publish_results)} betting recommendations")

        # Display results
        logger.info("=" * 50)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 50)

        if publish_results:
            for i, bet in enumerate(publish_results, 1):
                logger.info(f"Bet Recommendation #{i}:")
                logger.info(f"  Fixture: {bet.fixture_id}")
                logger.info(f"  Selection: {bet.selection}")
                logger.info(f"  Market: {bet.market_type.value}")
                logger.info(f"  Probability: {bet.probability:.2%}")
                logger.info(f"  Expected Value: {bet.expected_value:.4f}")
                logger.info(f"  Kelly Fraction: {bet.kelly_fraction:.2%}")
                logger.info(f"  Recommended Stake: {bet.recommended_stake:.2f} units")
                logger.info(f"  Confidence: {bet.confidence:.2%}")
                logger.info("")
        else:
            logger.info("No betting recommendations generated (this is expected with no real data)")
            logger.info("To get real recommendations, configure valid API keys in .env file")

        # Show CLV status
        clv_status = app.clv_calculator.get_clv_gate_status()
        logger.info("CLV Gate Status:")
        logger.info(f"  Gate Active: {clv_status['gate_active']}")
        logger.info(f"  Min Legs Required: {clv_status['min_legs_required']}")
        logger.info(f"  Mean CLV Threshold: {clv_status['mean_clv_threshold']}%")
        logger.info(f"  Current Phase: {clv_status['current_phase']}")

        return publish_results

    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Run the pipeline
    results = asyncio.run(run_full_pipeline())
    logger.info(f"Pipeline execution finished. Generated {len(results)} betting recommendations.")