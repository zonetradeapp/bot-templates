# AI Prompts для модификации 03-multi-symbol-aggregator

## Promt 1: cross-symbol confluence filter

```
@bot.py @claude.md

Цель: входим только если на двух BTCUSDT+ETHUSDT setup'ы согласуются.

1. Сейчас bot хранит recent_setups per symbol. Добавь функцию
   confluence_check(symbol_a, symbol_b, window_minutes=15):
   возвращает True если в последние 15 мин были setup'ы обоих
   символов в одном направлении.

2. Каждый новый setup → если confluence(setup.symbol, ANY_OTHER) проходит,
   логируй [CONFLUENCE] {symbol_a} + {symbol_b} both LONG @ {time}.

3. Сохраняй confluence-events в Redis list `agg:confluence` для anal'а.
```

## Promt 2: export в Parquet

```
@bot.py @claude.md

Добавь периодический export в Parquet файл для ML training:

1. Каждый час дамп всех bar events за этот час из Redis (agg:bar:*) в
   `/data/bars-YYYY-MM-DD-HH.parquet` (использовать pyarrow).
2. Колонки: timestamp, symbol, tf, open, high, low, close, volume.
3. После dump'а — clear Redis ключ (TTL уже 1h, но безопаснее explicit).
4. На startup — создать /data/ если не существует.
```

## Promt 3: премиум сигналы

```
@bot.py @claude.md

Добавь подписку на signal.three-drive-v11.<SYMBOL> (Starter tier) для
всех SYMBOLS. Handler @client.on("signal"):

1. Сохраняй в state.recent_premium_signals (deque maxlen=20).
2. В summary print дополни колонкой `prem[N↑/M↓]` где N+M = recent_premium.
3. Если получил subscribe_rejected (free tier) — log warning и
   продолжай работу без premium.
```

## Promt 4: time-of-day heatmap

```
@bot.py @claude.md

Цель: build dataset «в каком часу UTC чаще всего trap-flip setups для BTC».

1. Подписывайся на setup.three-drive-raw.BTCUSDT.
2. Для каждого setup извлекай hour-of-day (UTC) из confirmTime.
3. Поддерживай счётчик per (hour, direction).
4. Каждые 30 мин печатай ASCII heatmap (24 строки по часам, столбцы
   long/short count за всё время работы бота).
```
