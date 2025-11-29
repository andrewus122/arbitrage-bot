# Arbitrage Bot

Automated prediction market arbitrage scanner for Polymarket and OPINION markets.

## Description

This bot continuously monitors prices across multiple prediction markets and identifies arbitrage opportunities where price discrepancies exist between platforms.

**Supported Markets:**
- Polymarket (via public API)
- OPINION (via Selenium/browser automation)

## Features

- 🔍 Real-time price monitoring every 10 seconds
- 💰 Automated spread calculation with fee accounting
- 🚀 Identifies profitable arbitrage opportunities
- 📊 Tracks gross and net spreads
- 🔄 Resilient polling with automatic error recovery
- 📝 Console logging of all opportunities

## Requirements

- Python 3.8+
- Internet connection
- Chrome/Chromium browser (for Selenium)

See `requirements.txt` for Python dependencies.

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the bot: `python bot.py`

## How It Works

### Price Collection
- **Polymarket**: Fetches market data via HTTP API at `clob.polymarket.com`
- **OPINION**: Uses Selenium WebDriver to access JavaScript-rendered content

### Spread Calculation
The bot calculates both gross and net spreads:
- **Gross Spread**: Raw price difference between platforms
- **Net Spread**: Accounts for 1% trading fees per platform

### Opportunity Detection
Arbitrage opportunities are identified when:
- Net spread ≥ 2.5% (configurable threshold)
- Price pairs available on both platforms
- Market conditions are favorable

## Configuration

Edit these values in `bot.py` to customize behavior:
- `POLL_INTERVAL`: Time between scans (default: 10 seconds)
- `MIN_NET_SPREAD_PCT`: Minimum spread to report (default: 2.5%)
- `FEE_RATE`: Trading fee per platform (default: 0.01 or 1%)

## Output

The bot logs to console with timestamps and includes:
- Market ID and description
- YES and NO prices from each platform
- Calculated gross and net spreads
- Recommended arbitrage strategy

## Error Handling

The bot gracefully handles:
- Network failures
- API rate limiting
- Selenium/browser errors
- Market data inconsistencies

Monitoring continues automatically after errors are logged.

## Performance

- Typical scan cycle: 5-15 seconds
- Memory usage: ~100-200MB
- CPU usage: Low (<5% average)

## License

MIT License
