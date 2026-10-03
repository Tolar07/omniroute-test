#!/usr/bin/env python3
"""Test script to verify imports work correctly."""
import sys
import os

# Add the olp_xdv directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "olp_xdv_agent", "olp_xdv"))

print("Testing cache_refresh_scheduler import...")
try:
    import cache_refresh_scheduler
    print("cache_refresh_scheduler imported successfully")

    age = cache_refresh_scheduler.cache_age_minutes()
    fresh = cache_refresh_scheduler.is_cache_fresh()
    print(f"Cache age: {age} minutes (fresh: {fresh})")

except Exception as e:
    print(f"Failed to import cache_refresh_scheduler: {e}")

print("\nTesting booking.verify_fixtures import...")
try:
    from booking.verify_fixtures import is_cache_fresh, cache_age_minutes
    print("booking.verify_fixtures imported freshness functions successfully")

    age = cache_age_minutes()
    fresh = is_cache_fresh()
    print(f"Cache age: {age} minutes (fresh: {fresh})")

except Exception as e:
    print(f"Failed to import from booking.verify_fixtures: {e}")

print("\nTest complete.")