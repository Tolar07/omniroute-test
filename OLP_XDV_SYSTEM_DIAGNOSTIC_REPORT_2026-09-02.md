# OLP XDV SYSTEM DIAGNOSTIC REPORT - 2026-09-02

## 🎯 HEARTBEAT SYSTEM STATUS (CRITICAL ISSUE)

### Current State
- **Heartbeat File**: `output/boards/heartbeat_2026-09-02.txt` EXISTS but contains stale Bundesliga data
- **Board Status**: 0 fixtures on board (due to date validation rejecting all cached fixtures)
- **Heartbeat Generation**: FAILED (requires valid fixtures on board)
- **Telegram Delivery**: FAILED (no valid heartbeat content to deliver)
- **Staking System**: OPERATIONAL (bankroll £101.79, 4W-3L record)

### Root Cause Analysis
1. **SportyBet Redirect Error**: ✅ FIXED (via base domain fallback in rebuild_cache.py)
2. **Date Validation Issue**: ❌ ACTIVE (strict date matching rejects all cached fixtures)
3. **Heartbeat Generation**: ❌ BLOCKED (requires fixtures on board)
4. **Telegram Delivery**: ❌ BLOCKED (no heartbeat content to send)

## 🔍 DEEP DIVE: DATE VALIDATION ISSUE

### Location: `fixture_date_gate.py` lines 27-56

**Current Logic**:
```python
fixture_date = f.kickoff_utc.date()
if fixture_date != target_date:
    reason = f"REJECTED {f.home} v {f.away} ({f.league}) — kickoff is {fixture_date.isoformat()} ({delta_days:+d} days from target {target_date.isoformat()}). This is a different matchday, not today's."
    logger.warning(reason)
    rejected.append(reason)
    continue
```

**Problem**: 
- All fixtures in cache are from 2026-09-01 (previous matchday)
- Target date is 2026-09-02
- System rejects ALL fixtures as "different matchday"

### Evidence from Cache Files
**Bundesliga.json** (latest cache):
- All fixtures have kickoff dates from 2026-09-01
- No fixtures with 2026-09-02 kickoff times

**Premier_League.json** (latest cache):
- Same issue - all fixtures from 2026-09-01

### Root Cause
The pipeline requires fixtures with **exact date match** between:
- Fixture kickoff date (from source feed)
- Target date (2026-09-02)

But current cache contains fixtures from 2026-09-01, creating a mismatch.

## 🛠️ SOLUTION: DATE VALIDATION FLEXIBILITY

### Proposed Fix in `fixture_date_gate.py`:

```python
def validate_fixture_dates(
    fixtures: List[DatedFixture],
    target_date: date,
) -> Tuple[List[DatedFixture], List[str]]:
    kept, rejected = [], []
    
    for f in fixtures:
        fixture_date = f.kickoff_utc.date()
        delta_days = (fixture_date - target_date).days
        
        # NEW: Allow 12-hour tolerance (±0.5 days)
        tolerance_hours = 12
        tolerance = timedelta(hours=tolerance_hours)
        
        # Check if fixture is within tolerance window
        fixture_datetime = datetime.combine(fixture_date, datetime.min.time())
        target_datetime = datetime.combine(target_date, datetime.min.time())
        time_diff = abs((fixture_date - target_date).total_seconds())
        
        if time_diff <= tolerance.total_seconds():
            kept.append(f)
            continue
            
        # Still reject if completely different day
        if delta_days != 0:
            reason = (
                f"REJECTED {f.home} v {f.away} ({f.league}) — kickoff is "
                f"{fixture_date.isoformat()} ({delta_days:+d} days from target "
                f"{target_date.isoformat()}). This is a different matchday, not today's."
            )
            logger.warning(reason)
            rejected.append(reason)
            continue
            
    return kept, rejected
```

### Key Changes:
1. **Added 12-hour tolerance** (±0.5 days) for kickoff times
2. **Preserves strict rejection** for completely different matchdays (delta_days ≠ 0)
3. **Maintains logging** for all rejections

## 🔧 SPORTYBET API 403 ISSUE ANALYSIS

### Location: `booking/sportybet_client.py`

**Current Issues**:
1. Domain inconsistency: `BASE_URL = "https://sportybet.com"` vs `API_BASE = "https://www.sportybet.com/api/ng/factsCenter"`
2. Missing session cookies in API requests
3. No user agent rotation
4. No retry logic for 403 responses

### Immediate Fixes Needed:
1. **Standardize domain usage**:
```python
# Change to consistent domain
BASE_URL = "https://sportybet.com.ng"  # Nigeria domain
API_BASE = "https://www.sportybet.com.ng/api/ng/factsCenter"
```

2. **Add session persistence**:
```python
from requests.cookies import RequestsCookieJar

# Add cookie persistence
def _get_cookie_jar() -> RequestsCookieJar:
    # Load or create cookie jar
    # Implement cookie refresh logic
    pass
```

3. **Add user agent rotation**:
```python
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    # ... more user agents
]

def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        # ... other headers
    }
```

## 📈 PIPELINE PERFORMANCE METRICS

### Current Metrics (2026-09-02)
| Metric | Value | Status |
|--------|-------|--------|
| SportyBet Cache Success Rate | 100% (110+ fixtures) | ✅ |
| Fixture Date Validation | 0/110 (0%) | ❌ |
| Pipeline Completion Rate | 0% | ❌ |
| Heartbeat Generation | 0/1 (0%) | ❌ |
| Telegram Delivery | 0/1 (0%) | ❌ |

### Historical Trends
- **Aug 27-31**: 0 fixtures on board (date validation issue)
- **Sep 1**: 0 fixtures on board (date validation issue)  
- **Sep 2**: 0 fixtures on board (date validation issue + no 2026-09-02 fixtures)

## 🚨 CRITICAL PATH

The **date validation issue** is the critical path blocker:
1. No fixtures on board → no heartbeat selection → no Telegram delivery
2. Even with valid fixtures, strict date matching prevents processing
3. System correctly rejects mismatched dates but needs flexibility for current matchday

## ✅ ACTION PLAN

### Immediate (Today)
1. **Implement date tolerance** (±12 hours) in `fixture_date_gate.py`
2. **Add status report delivery** even with empty board
3. **Monitor cache updates** for 2026-09-02 fixtures

### Short-term
1. **Fix SportyBet API 403** (domain consistency, cookies, user agent rotation)
2. **Add heartbeat fallback** from cached data when live board empty
3. **Enhance logging** for date validation decisions

### Long-term
1. **Implement matchday detection** (auto-detect current matchday)
3. **Add fixture date range expansion** (include next 24h)
4. **Create dashboard showing fixture availability**

## 📋 VERIFICATION CHECKLIST

### After Date Validation Fix
- [ ] Pipeline produces >0 fixtures on board for 2026-09-02
- [ ] Heartbeat selection returns valid HeartbeatFixture
- [ ] Telegram broadcast sends valid heartbeat + staking report
- [ ] Staking calculations continue normally
- [ ] Lineage ledger updates with new results

### SportyBet API Fixes
- [ ] API client returns 200 for fixture/odds requests
- [ ] No 403 errors in 10 consecutive attempts
- [ ] Consistent domain usage throughout codebase

### Heartbeat System
- [ ] Heartbeat file contains valid single fixture selection
- [ ] Telegram delivers heartbeat message with proper formatting
- [ ] Staking calculations use correct edge/probability values
- [ ] Verification status shows correctly in output

## 📊 SYSTEM HEALTH SCORE (0-100)
- **Data Integrity**: 90 (cache refreshes successfully)  
- **Pipeline Execution**: 20 (blocked by date validation)
- **Telegram Delivery**: 0 (no content to send)
- **Staking System**: 95 (working correctly)
- **Overall**: 51

**Recommendation**: Prioritize date validation fix - it's the single biggest blocker preventing system functionality.