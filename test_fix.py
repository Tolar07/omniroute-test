from datetime import datetime, timedelta
import re as _re

def _flashscore_line_to_date(match_datetime: str, target_date: str | None = None, scrape_timestamp: str | None = None) -> str:
    """FlashScore match_1x2 `match_datetime` is '21.08. 20:00' (D.MM. HH:MM, no
    year) OR just '20:00' (HH:MM only for today's matches). Resolve to an ISO date.

    If `target_date` is provided (YYYY-MM-DD), resolve the year to match that
    date's month/day. Otherwise fall back to the current/next year within 400 days.

    For HH:MM only format, if scrape_timestamp is provided, use it to determine
    the correct date (assuming fixtures are scraped night before for next day's matches).
    """
    # First try full date format: "21.08. 20:00"
    m = _re.match(r"(\d{1,2})\.(\d{1,2})\.\s*(\d{1,2}):(\d{2})", match_datetime or "")
    if m:
        day, mon, hh, mm = (int(x) for x in m.groups())

        # If target_date given, use its year (and validate month/day match)
        if target_date:
            try:
                tgt = datetime.fromisoformat(target_date)
                # Ensure the day/month in match_datetime matches target_date
                if tgt.month == mon and tgt.day == day:
                    return target_date
                # If month/day don't match target_date, we can't resolve — return empty
                return ""
            except ValueError:
                pass  # fall through to fallback

        # Fallback: prefer a date in the current or next year, within ~12 months.
        now = datetime.now()
        for year in (now.year, now.year + 1):
            try:
                d = datetime(year, mon, day)
            except ValueError:
                continue
            if 0 <= (d - now).days <= 400:
                return d.strftime("%Y-%m-%d")
        return ""

    # Try HH:MM only format (e.g., "20:00" for today's matches)
    m = _re.match(r"^(\d{1,2}):(\d{2})$", match_datetime or "")
    if m:
        # When only time is given, we need to determine the date
        if scrape_timestamp:
            # Use the scrape timestamp to determine the correct date
            try:
                scrape_dt = datetime.fromisoformat(scrape_timestamp.replace('Z', '+00:00'))
                scrape_date = scrape_dt.date()
                hh, mm = (int(x) for x in m.groups())

                # Create candidate datetime for today at the specified time
                candidate_dt = datetime.combine(scrape_date, datetime.min.time().replace(hour=hh, minute=mm))

                # If the candidate time hasn't passed yet today, it's for today
                # Otherwise, it's for tomorrow (time has already passed)
                if candidate_dt >= scrape_dt:
                    return scrape_date.strftime("%Y-%m-%d")
                else:
                    next_day = scrape_date + timedelta(days=1)
                    return next_day.strftime("%Y-%m-%d")
            except ValueError:
                # Fall back to target_date if scrape timestamp parsing fails
                if target_date:
                    return target_date
                return ""
        elif target_date:
            # Legacy behavior: assume it's for the target_date
            return target_date
        # If we have neither scrape timestamp nor target_date, we can't determine the date
        return ""

    return ""

# Test cases
test_cases = [
    ('14:00', '2026-09-06T03:00:19.454691'),  # Everton vs Man Utd - should be 2026-09-06
    ('16:30', '2026-09-06T03:00:19.517874'),  # Arsenal vs Chelsea - should be 2026-09-06
    ('12.09. 15:00', '2026-09-06T03:00:19.587771'),  # Aston Villa vs Nottm Forest - should be 2026-09-12
    ('13.09. 14:00', '2026-09-06T03:00:19.996287'),  # Coventry vs Brighton - should be 2026-09-13
    ('05.09. 17:30', '2026-09-06T03:00:20.125794'),  # Hull vs Aston Villa - should be 2026-09-05
]

print("Testing fixed _flashscore_line_to_date function:")
print("Target date for validation: 2026-09-06")
print()

for match_datetime, scrape_timestamp in test_cases:
    result = _flashscore_line_to_date(match_datetime, target_date='2026-09-06', scrape_timestamp=scrape_timestamp)
    print(f'{match_datetime:>15} -> {result} (scrape: {scrape_timestamp[11:19]})')

print()
print("Expected results:")
print("14:00 -> 2026-09-06 (time 14:00 hasn't passed scrapetime 03:00)")
print("16:30 -> 2026-09-06 (time 16:30 hasn't passed scrapetime 03:00)")
print("12.09. 15:00 -> 2026-09-12 (full date format)")
print("13.09. 14:00 -> 2026-09-13 (full date format)")
print("05.09. 17:30 -> 2026-09-05 (full date format)")