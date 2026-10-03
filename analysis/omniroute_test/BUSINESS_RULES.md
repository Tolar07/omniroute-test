# Business Rules for OLP XDV Agent

Based on the assessment of the OLP XDV Agent codebase, the following business rules have been identified:

## Core Operational Rules

### HR35: No Fabrication
- **Priority**: P0
- **Description**: The system must not fabricate data. All data must come from verified sources.
- **Implementation**: Verified in code through source verification mechanisms
- **Confidence**: High

### Data Source Verification
- **Priority**: P0
- **Description**: Fixtures must be verified by at least 2 distinct sources before being considered valid
- **Implementation**: Should be implemented in fixtures_agent.py _apply_verification function
- **Current State**: Inconsistent - comment states ≥1 source check vs ≥2 source requirement in comments
- **Confidence**: Medium (due to inconsistency)

### CLV Gate Enforcement
- **Priority**: P0
- **Description**: The Closing Line Value (CLV) gate must be enforced before bet publication
- **Implementation**: Implemented in clv/closing_capture.py and referenced in agent_10_ceo
- **Current State**: GATE_FILE (brain/gate.json) may be absent or malformed
- **Confidence**: Medium (due to potential file issues)

### Architect Signoff Override
- **Priority**: P0
- **Description**: ARCHITECT_SIGNOFF can override the CLV gate for publication
- **Implementation**: Referenced in Protected Constants.md and Architecture.md
- **Current State**: Appears to be functioning as designed
- **Confidence**: High

### League Whitelist Compliance
- **Priority**: P1
- **Description**: Only fixtures from the 61 whitelisted leagues (from config/leagues.json) should be processed
- **Implementation**: Validated in fixtures_agent.py through load_whitelist and check_league_calendar
- **Confidence**: High

### Odds API Quota Management
- **Priority**: P1
- **Description**: Odds API quota is 1/500 - prices for non-deploy leagues should be "NO DATA ? PENDING"
- **Implementation**: Referenced in Standing reminders from the code
- **Confidence**: High

### Paper/Live Transition Protocol
- **Priority**: P2
- **Description**: System operates in Phase-3 live with paper/live transition - bets are never placed automatically
- **Implementation**: Architect turns booking codes into money manually
- **Confidence**: High

### SportyBet Integration Requirements
- **Priority**: P1
- **Description**: All bets must be priced on SportyBet's own line with booking codes generated
- **Implementation**: Through booking/bridge.py using Playwright
- **Confidence**: High

### Telegram Delivery Requirement
- **Priority**: P1
- **Description**: Daily board and bet codes must be delivered to Telegram
- **Implementation**: Through output/telegram_webhook.py
- **Confidence**: High

## Data Integrity Rules

### CSV Season Data Integrity
- **Priority**: P2
- **Description**: Season CSV data files must maintain integrity for backtesting
- **Implementation**: Stored in olp_xdv_agent/olp_xdv/data/ with naming like Premier_League_2324.csv
- **Confidence**: High

### SQLite Brain Persistence
- **Priority**: P2
- **Description**: The SQLite database in brain/ must persist CLV data and migrations
- **Implementation**: Through brain/store.py with migrations v1-v8
- **Confidence**: High

### Cache Management
- **Priority**: P2
- **Description**: Data cache must be properly maintained to avoid stale data
- **Implementation**: CSV cache in olp_xdv_agent/olp_xdv/data/cache/
- **Confidence**: Medium (observations show potential stale cache files)

## Security Rules

### Credential Management
- **Priority**: P0
- **Description**: All credentials must be stored in .env file (gitignored) never committed
- **Implementation**: .env.example provides template, .env contains real values
- **Confidence**: High

### API Key Rotation
- **Priority**: P1
- **Description**: API keys must be rotatable without code changes
- **Implementation**: Read from environment variables (APIFOOTBALL_KEY, etc.)
- **Confidence**: High

### Admin Authentication
- **Priority**: P1
- **Description**: Admin dashboard access requires HTTP Basic authentication
- **Implementation**: Username "architect" with strong password
- **Confidence**: High

## System Behavior Rules

### Daily Pipeline Execution
- **Priority**: P2
- **Description**: Pipeline must execute daily to produce today-only bet
- **Implementation**: Through orchestrator.py main loop
- **Confidence**: High

### Board Generation
- **Priority**: P2
- **Description**: Must generate a today-only betting board (Acca A + split accas + singles)
- **Implementation**: Through olp_xdv_pipeline.py and render_board_from_pipeline
- **Confidence**: High

### Statistical Gate Monitoring
- **Priority**: P2
- **Description**: Statistical gate requires 12/30 legs with CLV, mean CLV ?1.631%
- **Implementation**: Monitored but currently NOT met - runs on ARCHITECT_SIGNOFF override
- **Confidence**: High

## Disabled/Deprecated Features

### WhatsApp Integration (KILLED)
- **Priority**: P0
- **Description**: WhatsApp integration was killed per Architect order ID412 on 2026-08-06
- **Implementation**: WHATSAPP_ENABLED=0, credentials commented out in .env
- **Confidence**: High
- **Note**: Do not re-enable without Architect approval

### Email Integration (OFF)
- **Priority**: P2
- **Description**: Email integration via SMTP is currently OFF
- **Implementation**: EMAIL_* variables commented in .env
- **Confidence**: High
- **Note**: Leave OFF unless explicitly ratified

## Implementation References

Key files that implement these rules:
- `olp_xdv_agent/olp_xdv/fixtures_agent.py` - Data ingestion and verification
- `olp_xdv_agent/olp_xdv/config/leagues.json` - League whitelist
- `olp_xdv_agent/olp_xdv/clv/closing_capture.py` - CLV gate enforcement
- `olp_xdv_agent/olp_xdv/olp_xdv_pipeline.py` - Main pipeline logic
- `olp_xdv_agent/olp_xdv/brain/store.py` - SQLite persistence
- `olp_xdv_agent/olp_xdv/booking/bridge.py` - SportyBet integration
- `olp_xdv_agent/olp_xdv/output/telegram_webhook.py` - Telegram delivery
- `olp_xdv_agent/olp_xdv/config.py` - Phase, capital gate, thresholds
- `olp_xdv_agent/olp_xdv/.env` - Environment variables (credentials)
- `olp_xdv_agent/olp_xdv/docs/obsidian-vault/Protected Constants.md` - Off-limits constants
- `olp_xdv_agent/olp_xdv/docs/obsidian-vault/Decisions Log.md` - Architect directives