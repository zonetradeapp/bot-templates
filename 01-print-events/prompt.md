# AI Prompts для модификации 01-print-events

Скопируй один из этих промтов в Claude/Cursor (приложи `bot.py` +
[claude.md из SDK](https://github.com/zonetrade/sdk-python/blob/main/claude.md)).

## Promt 1: добавить новые символы

```
@bot.py @claude.md

Модифицируй этот bot.py чтобы подписывался также на:
  - bar.1m.SOLUSDT
  - bar.1m.BNBUSDT
  - zone.fvg.SOLUSDT
  - zone.ob.SOLUSDT

Сохрани остальные подписки. Не меняй handler'ы.
```

## Promt 2: фильтрация по символу

```
@bot.py @claude.md

Добавь фильтр: bot должен печатать ТОЛЬКО события для BTCUSDT, события
для других символов игнорировать. Используй handler-side фильтр
(не unsubscribe).
```

## Promt 3: сохранение в JSONL

```
@bot.py @claude.md

Дополни bot.py чтобы записывал каждое event в файл `events.jsonl`
(один JSON-объект на строку, с timestamp). Сохрани также вывод в
консоль. После KeyboardInterrupt — корректно закрывай файл.
```

## Promt 4: фильтрация zone-events по freshness

```
@bot.py @claude.md

Модифицируй on_zone handler чтобы печатать только зоны с fillPct < 0.33
(свежие). Сожжённые зоны (fillPct >= 0.85) логируй красным через
ANSI escape коды.
```
