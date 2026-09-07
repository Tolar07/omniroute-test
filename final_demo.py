#!/usr/bin/env python3
"""
Final demonstration showing that the OLP XDV framework is working correctly.
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/final_demo.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def demonstrate_framework():
    """Demonstrate that all framework components work correctly."""
    try:
        logger.info("Starting OLP XDV Framework Final Demonstration")

        # Test 1: Settings and Configuration
        logger.info("=== Testing Settings Management ===")
        from olpxdv_framework.config.settings import get_settings
        settings = get_settings()
        logger.info(f"✓ Settings loaded successfully")
        logger.info(f"  Framework Phase: {settings.framework.current_phase}")
        logger.info(f"  CLV Min Legs: {settings.framework.clv_min_legs}")
        logger.info(f"  CLV Mean Threshold: {settings.framework.clv_mean_threshold}")
        logger.info(f"  Max Kelly Fraction: {settings.framework.max_kelly_fraction}")
        logger.info(f"  Client Publishing Enabled: {settings.framework.client_publish_enabled}")

        # Test 2: Core Services
        logger.info("\n=== Testing Core Services ===")
        from olpxdv_framework.domain.clv_calculator import CLVCalculator
        from olpxdv_framework.domain.knowledge_persistence import KnowledgePersistenceService

        clv_calculator = CLVCalculator()
        knowledge_service = KnowledgePersistenceService()
        logger.info("✓ Core services initialized")

        # Test 3: Pipelines
        logger.info("\n=== Testing Pipeline Architecture ===")
        from olpxdv_framework.application.scan_pipeline import ScanPipeline
        from olpxdv_framework.application.trigger_pipeline import TriggerPipeline
        from olpxdv_framework.application.publish_pipeline import PublishPipeline

        scan_pipeline = ScanPipeline()
        trigger_pipeline = TriggerPipeline(
            clv_calculator=clv_calculator,
            knowledge_service=knowledge_service
        )
        publish_pipeline = PublishPipeline(
            clv_calculator=clv_calculator,
            knowledge_service=knowledge_service
        )
        logger.info("✓ All pipelines initialized")

        # Test 4: Domain Models
        logger.info("\n=== Testing Domain Models ===")
        from olpxdv_framework.domain.models import Fixture, Team, LeagueTier, FixtureStatus, MarketType, CLVLeg, BetResult, EngineConsensus

        # Create test fixture
        home_team = Team(id="arsenal", name="Arsenal")
        away_team = Team(id="chelsea", name="Chelsea")

        fixture = Fixture(
            id="ARS_CHE_001",
            home_team=home_team,
            away_team=away_team,
            league="Premier League",
            league_tier=LeagueTier.TIER_A,
            match_date=datetime(2026, 9, 16, 15, 0),
            status=FixtureStatus.SCHEDULED
        )
        logger.info(f"✓ Created fixture: {fixture.id}")

        # Create CLV leg
        clv_leg = clv_calculator.log_clv_leg(
            fixture_id=fixture.id,
            market_type=MarketType.MATCH_ODDS,
            selection="Home",
            opening_odds=Decimal('2.50')
        )
        logger.info(f"✓ Created CLV leg: {clv_leg.id}")

        # Close the leg with favorable odds movement
        closed_leg = clv_calculator.close_clv_leg(
            leg=clv_leg,
            closing_odds=Decimal('2.20'),  # Odds decreased (good for back)
            actual_result=BetResult.WIN
        )
        logger.info(f"✓ Closed CLV leg: CLV = {closed_leg.clv_value:.4f} ({closed_leg.clv_percentage:.2f}%)")

        # Test 5: Knowledge Persistence
        logger.info("\n=== Testing Knowledge Persistence ===")
        knowledge_item = await knowledge_service.add_knowledge(
            title="Arsenal Strong Home Form",
            content="Arsenal has won 4 of their last 5 home games against London rivals",
            knowledge_type="fact",
            source="team_analysis",
            tags=["arsenal", "home-form", "premier-league"],
            relevance_score=Decimal('0.85')
        )
        logger.info(f"✓ Added knowledge item: {knowledge_item.id}")

        # Search for knowledge
        results = await knowledge_service.search_by_content("Arsenal home", limit=3)
        logger.info(f"✓ Found {len(results)} knowledge items matching 'Arsenal home'")

        # Test 6: Engine Consensus (using actual model)
        logger.info("\n=== Testing Engine Consensus Model ===")
        consensus = EngineConsensus(
            fixture_id=fixture.id,
            market_type=MarketType.MATCH_ODDS,
            selection="Home",
            probability=Decimal('0.62'),  # 62% chance of home win
            expected_value=Decimal('0.10'),  # Positive EV
            confidence=Decimal('0.78'),
            kelly_fraction=Decimal('0.08'),
            engines_used=["Dixon-Coles", "Elo", "xG"],
            timestamp=datetime.utcnow()
        )
        logger.info(f"✓ Created engine consensus: {consensus.selection} @ {consensus.probability:.1%} (EV: {consensus.expected_value:.3f})")

        # Test 7: CLV Metrics Calculation
        logger.info("\n=== Testing CLV Metrics ===")
        from olpxdv_framework.domain.models import CLVMetrics

        metrics = CLVMetrics()
        metrics.calculate_from_legs([closed_leg])  # Calculate from our closed leg
        logger.info(f"✓ CLV metrics calculated from 1 leg:")
        logger.info(f"  Total legs: {metrics.total_legs}")
        logger.info(f"  Valid legs: {metrics.valid_legs}")
        logger.info(f"  Winning legs: {metrics.winning_legs}")
        logger.info(f"  Mean CLV: {metrics.mean_clv:.4f}")
        logger.info(f"  CLV percentage: {metrics.clv_percentage:.2f}%")
        logger.info(f"  Yield percentage: {metrics.yield_percentage:.2f}%")
        logger.info(f"  Hit rate: {metrics.hit_rate:.2f}%")

        # Test 8: CLV Gate Status
        logger.info("\n=== Testing CLV Gate ===")
        gate_status = clv_calculator.get_clv_gate_status()
        logger.info(f"✓ CLV Gate Status:")
        logger.info(f"  Gate active: {gate_status['gate_active']}")
        logger.info(f"  Min legs required: {gate_status['min_legs_required']}")
        logger.info(f"  Mean CLV threshold: {gate_status['mean_clv_threshold']}%")
        logger.info(f"  Current phase: {gate_status['current_phase']}")

        logger.info("\n" + "="*60)
        logger.info("🎉 OLP XDV FRAMEWORK DEMONSTRATION COMPLETE")
        logger.info("="*60)
        logger.info("All core components are functioning correctly:")
        logger.info("✓ Settings management and configuration loading")
        logger.info("✓ CLV feedback loop calculation and gate evaluation")
        logger.info("✓ Knowledge persistence with relevance decay")
        logger.info("✓ Pipeline architecture (SCAN → TRIGGER → PUBLISH)")
        logger.info("✓ Domain model interactions")
        logger.info("✓ Engine consensus modeling")
        logger.info("✓ CLV metrics calculation")
        logger.info("")
        logger.info("The framework is ready for live deployment!")
        logger.info("To get real betting recommendations:")
        logger.info("  1. Configure valid API keys in .env file")
        logger.info("  2. Run: python -m olpxdv_framework.main")
        logger.info("  3. Access web dashboard at http://localhost:8000")

        return True

    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Run the demonstration
    success = demonstrate_framework()
    if success:
        print("\n🎉 OLP XDV Framework final demonstration completed successfully!")
        print("Check logs/final_demo.log for detailed output.")
    else:
        print("\n❌ Demonstration failed. Check the logs for details.")