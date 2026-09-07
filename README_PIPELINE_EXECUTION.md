# How to Execute the Full OLP XDV Pipeline

## Overview
This document explains how to run the complete OLP XDV pipeline to generate betting recommendations.

## Prerequisites
1. Python 3.11 or higher installed
2. All dependencies installed (run `pip install -e .[dev]`)
3. Valid API keys configured in `.env` file for live data (optional for demo mode)

## Execution Methods

### Method 1: Run the Demo Pipeline Script
The simplest way to see the pipeline in action is to run the demo script:

```bash
python run_full_pipeline.py
```

This will:
- Initialize all framework components
- Run the SCAN pipeline (will use mock data if no API keys are configured)
- Run the TRIGGER pipeline to identify value bets
- Run the PUBLISH pipeline to generate final recommendations
- Display the betting recommendations and CLV gate status

### Method 2: Run Individual Pipeline Components
You can also run each pipeline separately for more control:

```bash
# Start the web dashboard (on http://localhost:8000)
python -m olpxdv_framework.main

# Or run specific pipelines programmatically:
from olpxdv_framework.application.scan_pipeline import ScanPipeline
from olpxdv_framework.application.trigger_pipeline import TriggerPipeline
from olpxdv_framework.application.publish_pipeline import PublishPipeline
from olpxdv_framework.domain.clv_calculator import CLVCalculator
from olpxdv_framework.domain.knowledge_persistence import KnowledgePersistenceService

# Initialize components
clv_calc = CLVCalculator()
knowledge_svc = KnowledgePersistenceService()
scan_pipe = ScanPipeline()
trigger_pipe = TriggerPipeline(clv_calculator=clv_calc, knowledge_service=knowledge_svc)
publish_pipe = PublishPipeline(clv_calculator=clv_calc, knowledge_service=knowledge_svc)

# Run pipelines
scan_results = await scan_pipe.run_scan_cycle()
trigger_results = await trigger_pipe.run_trigger_cycle(scan_results)
publish_results = await publish_pipe.run_publish_cycle(trigger_results)
```

### Method 3: Use the Main Application Entry Point
For the full desktop application experience:

```bash
python -m olpxdv_framework.main
```

This will start:
- The SCAN/TRIGGER/PUBLISH pipeline scheduler
- The web dashboard (accessible at http://localhost:8000)
- The Telegram bot adapter (if configured)
- The vault-memory synchronization agent
- System tray icon and notifications (desktop mode)

## Expected Output

When running the pipeline, you should see output similar to:

```
[INFO] Starting OLP XDV Full Pipeline Execution
[INFO] Framework Phase: 3
[INFO] CLV Min Legs: 30
[INFO] Client Publishing Enabled: False
[INFO] Running SCAN pipeline...
[INFO] SCAN pipeline completed. Found 5 consensus items
[INFO] Running TRIGGER pipeline...
[INFO] TRIGGER pipeline completed. Found 2 value bets
[INFO] Running PUBLISH pipeline...
[INFO] PUBLISH pipeline completed. Generated 1 betting recommendations
[INFO] ==================================================
[INFO] PIPELINE EXECUTION COMPLETE
[INFO] ==================================================
[INFO] Bet Recommendation #1:
[INFO]   Fixture: DEMO_FIXTURE_001
[INFO]   Selection: Home
[INFO]   Market: MATCH_ODDS
[INFO]   Probability: 65.00%
[INFO]   Expected Value: 0.1200
[INFO]   Kelly Fraction: 8.00%
[INFO]   Recommended Stake: 0.08 units
[INFO]   Confidence: 80.00%
[INFO]
[INFO] CLV Gate Status:
[INFO]   Gate Active: True
[INFO]   Min Legs Required: 30
[INFO]   Mean CLV Threshold: 0.00%
[INFO]   Current Phase: 3
```

## Configuration Notes

### For Live Data
To get real betting recommendations instead of mock data:
1. Obtain API keys from:
   - [The Odds API](https://the-odds-api.com/)
   - [API-Football](https://www.api-football.com/)
2. Add them to your `.env` file:
   ```
   API__ODDS_API_KEY=your_actual_odds_api_key
   API__API_FOOTBALL_KEY=your_actual_api_football_key
   ```

### For SportyBet Integration
To enable actual betting via SportyBet:
1. Configure your SportyBet credentials in `.env`:
   ```
   SPORTYBET_USERNAME=your_username
   SPORTYBET_PASSWORD=your_password
   SPORTYBET_BASE_URL=https://www.sportybet.com
   ```
2. The pipeline will generate booking codes that can be used on the SportyBet platform

### For Telegram Notifications
To receive betting recommendations via Telegram:
1. Create a bot using @BotFather on Telegram
2. Get your chat ID (you can get this from @userinfobot)
3. Add to `.env`:
   ```
   API__TELEGRAM_BOT_TOKEN=your_bot_token
   API__TELEGRAM_CHAT_ID=your_chat_id
   API__TELEGRAM_BOARD_DELIVERY_ENABLED=1
   ```

## Pipeline Stages Explained

1. **SCAN Pipeline**: 
   - Ingests fixture and odds data from configured APIs
   - Validates data for fabrication and quality issues
   - Runs engine suite (Dixon-Coles, Elo, xG) to generate consensus predictions
   - Integrates relevant knowledge from persistence system
   - Outputs EngineConsensus objects

2. **TRIGGER Pipeline**:
   - Validates consensus data from SCAN pipeline
   - Analyzes for value betting opportunities (positive expected value)
   - Calculates Kelly criterion stakes
   - Applies risk management rules
   - Outputs qualified betting opportunities

3. **PUBLISH Pipeline**:
   - Evaluates CLV gate to ensure model calibration is sufficient
   - Applies final validation (odds changes, market conditions)
   - Generates final betting recommendations
   - Produces dual output (console + web dashboard)
   - Creates SportyBet booking codes if enabled
   - Sends Telegram notifications if configured

## Troubleshooting

### Common Issues
1. **"No data found"**: 
   - Check that API keys are valid and not rate-limited
   - Verify network connectivity to external APIs
   - Check logs for specific error messages

2. **Configuration errors**:
   - Verify `.env` file is in the project root
   - Check that all required fields are present
   - Ensure values are in correct format (especially boolean values)

3. **Import errors**:
   - Make sure you're running from the project root directory
   - Verify all dependencies are installed: `pip install -e .[dev]`
   - Check Python version is 3.11+

### Logs
- Application logs: `logs/olpxdv.log`
- Pipeline execution logs: Console output during execution
- Error logs: Check both console and log files for tracebacks

## Next Steps After Successful Execution

1. **Monitor Performance**: Check the CLV gate status to see how well your models are calibrated
2. **Review Recommendations**: Evaluate the generated bets against actual match outcomes
3. **Adjust Parameters**: Tune framework settings in `.env` based on performance:
   - `FRAMEWORK__CLV_MIN_LEGS`: How many bets needed for CLV evaluation
   - `FRAMEWORK__CLV_MEAN_THRESHOLD`: Minimum CLV percentage required
   - `FRAMEWORK__MAX_KELLY_FRACTION`: Maximum fraction of bankroll to bet
   - `FRAMEWORK__MIN_EDGE_FOR_PUBLISH`: Minimum edge required to publish bets

4. **Scale Up**: 
   - Add more leagues to `FRAMEWORK__WHITELISTED_LEAGUES`
   - Decrease `FRAMEWORK__CLV_WINDOW_HOURS` for more timely closing lines
   - Increase `FRAMEWORK__MODEL_REUSE_DAYS` for more stable models

## Safety Features
The framework includes multiple safety mechanisms:
- **Protected Constants**: Critical parameters cannot be changed without explicit override
- **CLV Gate**: Prevents publishing when model calibration is insufficient
- **Maximum Exposure Limits**: Controls daily and per-bet risk
- **Minimum Edge Requirements**: Ensures only sufficiently profitable bets are published
- **Fabrication Detection**: Flags potentially manipulated or incorrect odds data

The framework is designed for responsible betting with built-in risk management and model calibration safeguards.