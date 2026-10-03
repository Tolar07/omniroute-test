#!/usr/bin/env python3
"""
Test script to verify the league verification integration works
"""

import sys
from pathlib import Path

# Add the OLP XDV module to path
sys.path.insert(0, str(Path(__file__).parent / "olp_xdv_agent" / "olp_xdv"))

def test_league_verifier_import():
    """Test that we can import the league verifier"""
    try:
        from engine.league_verifier import LeagueVerifier, run_daily_league_verification
        print("✓ LeagueVerifier imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import LeagueVerifier: {e}")
        return False

def test_verification():
    """Test running the verification"""
    try:
        from engine.league_verifier import run_daily_league_verification
        report = run_daily_league_verification("flashscore_leagues_sep4.json")
        print(f"✓ Verification completed: {report['status']}")
        print(f"  Coverage: {report['covered_count']}/{report['whitelisted_count']} leagues ({report['coverage_percentage']}%)")
        return True
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False

def test_pipeline_import():
    """Test that we can import the pipeline with our modifications"""
    try:
        import olp_xdv_pipeline
        print("✓ OLP XDV pipeline imported successfully")
        # Check if our imports are present
        if hasattr(olp_xdv_pipeline, 'LeagueVerifier'):
            print("✓ LeagueVerifier found in pipeline imports")
        else:
            print("⚠ LeagueVerifier not found in pipeline attributes (may be local import)")
        return True
    except Exception as e:
        print(f"✗ Failed to import OLP XDV pipeline: {e}")
        return False

if __name__ == "__main__":
    print("Testing League Verification Integration")
    print("=" * 50)

    tests = [
        test_league_verifier_import,
        test_verification,
        test_pipeline_import
    ]

    results = []
    for test in tests:
        results.append(test())
        print()

    passed = sum(results)
    total = len(results)

    print(f"Results: {passed}/{total} tests passed")
    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)