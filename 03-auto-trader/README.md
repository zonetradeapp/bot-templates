# 04 — Auto Trader (paper-trading)

Полный цикл «сигнал → paper-ордер → fill → PnL» на нашей виртуальной бирже. Без реальных денег, без Binance API — только Zonetrade.

## Use case

- Тестировать стратегию (три-драйв / trap-flip / свою) end-to-end перед mainnet
- Видеть как наш PnL накапливается на реальных сигналах в живом времени
- Базовый скелет для своего бота: добавь фильтры, position sizing, telegram-нотификации

## Чем отличается от 02 (Binance bridge)

| Что              | 02 (Binance bridge)            | 04 (auto-trader, этот)         |
|------------------|--------------------------------|--------------------------------|
| Куда идут ордера | На реальный Binance Futures    | На наш `/api/v1/orders`        |
| Деньги           | Реальные USDT                  | Виртуальные «coins»            |
| Fill source      | Binance matching engine        | Cron `app:check-orders` против Binance spot price |
| Fill уведомления | `futures_account` polling      | WS push `user.<id>.order`      |
| Риск             | Реальный                       | Нулевой                        |

Когда стратегия отработана на (04) — переключаешься на (02) с теми же сигналами.

## Quick start

```bash
cd 04-auto-trader
pip install -r requirements.txt
export ZT_API_KEY=zt_your_key
python bot.py
```

Будет лог такого вида:

```
mode=LIVE (paper) strategy=three-drive-v11 symbols=['BTCUSDT', 'ETHUSDT'] amount=$100 min_rr=1.5
subscribed to order events
[PLACED #42] BTCUSDT long @81000 SL=80700 TP1=81600 TP2=82200 TP3=83000 RR=2.00 type=stop_market qty=0.006173
[FILLED #42] BTCUSDT @81015 qty=0.006173
[CLOSED #42] BTCUSDT tp @81604 PnL=+1.96
```

## Configuration (env vars)

| Var               | Default                     | Описание                                          |
|-------------------|-----------------------------|---------------------------------------------------|
| `ZT_API_KEY`      | (required)                  | Получить на https://zonetrade.app/bot/api-keys    |
| `ZT_SYMBOLS`      | `auto`                      | `auto` — взять `User.signalSymbols` (whitelist из настроек уведомлений, default BTC/ETH/SOL/BNB/XRP). CSV — explicit override |
| `ZT_STRATEGY`     | `three-drive-v11`           | `three-drive-raw` (Free, без HTF-фильтра) \| `three-drive-v11` (Starter, HTF-filtered) \| `trap-flip` (Pro) |
| `ZT_RISK_PERCENT` | (unset)                     | **risk-based**: убыток на SL = `risk_% × balance`. qty подстраивается под SL distance, leverage 5× применяется backend'ом. Приоритетнее AMOUNT_*. |
| `ZT_AMOUNT_PERCENT` | (unset)                   | margin-based: `%` balance как margin (notional = margin × leverage). Реальный риск зависит от SL distance. |
| `ZT_AMOUNT_USD`   | `100`                       | Fallback fixed margin. Используется если PERCENT и RISK не заданы. |
| `ZT_LEVERAGE`     | `5`                         | Должно совпадать с `OrderService::LEVERAGE` на бэкенде. |
| `ZT_MIN_RR`       | `1.5`                       | Минимальный RR для входа                          |
| `ZT_DRY_RUN`      | `0`                         | `1` — печатать что бы сделал, не отправлять       |
| `ZT_BASE_URL`     | `wss://zonetrade.app/external-signals` | WS endpoint. Переопределить для dev/staging |
| `ZT_API_ORDERS_URL` | (auto-derive из `ZT_BASE_URL`) | Origin REST `/api/v1/orders/*` (без пути). В local dev WS и REST на разных портах — задай явно (`http://localhost:8000`) |

## Что под капотом

1. SDK подписывается на `signal.<strategy>.<SYMBOL>` для каждого символа
2. Параллельно: `client.subscribe_orders()` — подписка на push-канал своих ордеров
3. На каждый сигнал → `client.place_order(...)` → POST `/api/v1/orders`
4. Backend создаёт `wait`-ордер, cron `app:check-orders` его активирует при достижении entry, cron `app:check-trades` закрывает по TP/SL
5. На каждый статус-change приходит WS-event `{action, reason, pnl}` → печатается

## Customization

См. `prompt.md` — готовые AI-промты для модификации (фильтры, position sizing, оповещения).

## Limitations

- Нет idempotency: если бот рестартанёт и signal придёт повторно, создастся дубль. Идея — `client_order_id` параметр, см. open question #4 в `06-orders-v1-implemented.md`.
- Нет rate-limit на стороне backend'а пока. Если стратегия слишком частая — будет проблема (open question #3).
- `cancelled`-event не публикуется backend'ом сейчас (только `closed.manual`). Cancel `wait`-ордера снаружи (например из dashboard UI) бот не увидит. Открытый вопрос #5.

## Связь с docs

Полный контракт REST API: [`docs/description/18-bot-platform/06-orders-v1-implemented.md`](../../docs/description/18-bot-platform/06-orders-v1-implemented.md)
