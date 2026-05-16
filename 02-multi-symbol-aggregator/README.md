# 03 — Multi-symbol Aggregator

Бот следит за 5 символами параллельно, агрегирует bars / setups / zones
в Redis. Каждые 60 сек печатает per-symbol summary.

**Tier: Free** (если только raw setups + bars) или **Starter** (с
`signal.three-drive-v11.*` — нужно edit'ить bot.py).

## Use case

- **Аналитика**: топ symbols по setup count, time-of-day patterns.
- **ML features**: исторические bars + setup-events → training dataset.
- **Cross-symbol filter**: «вход BTC long ТОЛЬКО если за последний час
  и ETH long-bias». Для этого расширь bot.py — Redis уже хранит state.

## Quick start

```bash
cd 03-multi-symbol-aggregator
pip install -r requirements.txt
docker run -d -p 6379:6379 redis:7  # если Redis не запущен
export ZT_API_KEY=zt_your_key
python bot.py
```

Output (примерно каждые 60 сек):
```
──────────────────────────────────────────────────
BTCUSDT: bars=58 setups[2↑/1↓] zones=12
ETHUSDT: bars=58 setups[3↑/0↓] zones=15
SOLUSDT: bars=58 setups[1↑/2↓] zones=8
BNBUSDT: bars=58 setups[0↑/1↓] zones=10
XRPUSDT: bars=58 setups[2↑/2↓] zones=9
```

## Redis schema

| Key | Type | Содержимое |
|-----|------|------------|
| `agg:bar:<SYMBOL>:<TF>` | string (JSON) | Last bar event, TTL 1h |
| `agg:setups:<SYMBOL>` | list | Last 50 setup events |

Можно подключать другие сервисы (Grafana / Jupyter / etc.) которые
читают Redis для визуализации.

## Customization

См. `prompt.md` — готовые Claude/Cursor промты для:
- Добавить более premium-каналы (требует Starter+ tier).
- Cross-symbol corr filter.
- Export в Parquet / Pandas для ML.
