# 01 — Print Events

Минимальный бот. Подключается к Zonetrade WS, подписывается на 7 каналов,
печатает каждое событие. Tier: **Free**.

## Use case

- Проверить что API key работает.
- Понять формат event'ов перед написанием своей стратегии.
- Дебажить инфраструктуру (network, firewall).

## Quick start

```bash
cd 01-print-events
pip install -r requirements.txt
export ZT_API_KEY=zt_your_key
python bot.py
```

Ожидаемый output:
```
Connecting to Zonetrade WS...
[hello] user=42 tier=free
[bar]    BTCUSDT 1m close=81080 vol=12.34
[zone]   BTCUSDT FvgZone bullish top=2304.18 bot=2293.77 fill=0.21
[struct] BTCUSDT bos up price=81250
[setup]  BTCUSDT three-drive-raw long entry=81100
...
```

## Customization

- Изменить символы: правь list в `subscribe=[...]` параметре `client.run()`.
- Изменить таймфрейм: `bar.1m.X` → `bar.5m.X` / `bar.1h.X` / etc.
- Pro tier: добавить `signal.trap-flip.BTCUSDT` для premium сигналов.

## AI customization

См. [`prompt.md`](./prompt.md) — готовые промты для Claude/Cursor.
