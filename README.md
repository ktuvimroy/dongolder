# Gold Signal Bot

XAU/USD trading signal bot with technical analysis and Telegram integration.

## Features

- Real-time gold price data from Alpha Vantage
- Technical analysis indicators (RSI, MACD, Bollinger Bands)
- Telegram notifications for trading signals
- Rate-limited API access (respects free tier limits)

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your Alpha Vantage API key
```

## Development

```bash
# Run tests
pytest
```
