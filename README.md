# Zonetrade Bot Templates

Ready-to-run Python bots built on top of
[`zonetrade-sdk`](https://github.com/zonetradeapp/zonetrade-sdk):
patterns from a minimal "print all events" up to a custom detector and
paper trading. The goal — `git clone`, fill `.env`, `python bot.py` —
and you're on the WS stream.

## Templates

| # | Name | Level | What it shows |
|---|------|-------|---------------|
| 01 | [`print-events`](./01-print-events) | beginner | Minimal bot: connect to WS → print every event. For debugging and getting familiar with the stream. |
| 02 | [`multi-symbol-aggregator`](./02-multi-symbol-aggregator) | intermediate | Listens to 5+ symbols in parallel and aggregates events into Redis. A pattern for dashboards and alerting. |
| 03 | [`auto-trader`](./03-auto-trader) ⭐ | intermediate | Signal → paper-order on the Zonetrade virtual exchange → fill/PnL pushed back. **Recommended starting point** — no real-money risk. |
| 04 | [`custom-3drive-from-fractals`](./04-custom-3drive-from-fractals) | advanced | Build your own 3-drive detector on top of the `structure-snapshot` + fractal stream. An example of how to derive custom signals from base events. |
| 05 | [`indicator-plugin-demo`](./05-indicator-plugin-demo) | intermediate | Bot as an indicator: uses the official `FractalsPlugin` to draw HH/HL/LH/LL markers onto your own chart. Reference for writing your own visual plugin. |

## Quickstart

```bash
# 1. Install the SDK
pip install git+https://github.com/zonetradeapp/zonetrade-sdk

# 2. Clone the templates
git clone https://github.com/zonetradeapp/bot-templates
cd bot-templates/03-auto-trader

# 3. Fill in .env (grab the API key at https://zonetrade.app/integration/api-keys)
cp .env.example .env
$EDITOR .env

# 4. Run
pip install -r requirements.txt
python bot.py
```

## SDK + reference

- SDK: <https://github.com/zonetradeapp/zonetrade-sdk>
- AI-agent guide (Claude / Cursor): [`claude.md`](https://github.com/zonetradeapp/zonetrade-sdk/blob/main/claude.md)
- Pricing: <https://zonetrade.app/integration/pricing>

## License

MIT (see [LICENSE](./LICENSE))
