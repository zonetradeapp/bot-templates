# AI Prompts для модификации 04-auto-trader

Скопируй один из этих промтов в Claude/Cursor вместе с `bot.py` + [`claude.md` SDK](https://github.com/zonetrade/sdk-python/blob/main/claude.md).

## Promt 1: дополнительный фильтр HTF-структуры

```
@bot.py @claude.md

Добавь фильтр в этого auto-trader'а: не создавать ордер если последний
CHoCH/BoS на 1h противоречит направлению сигнала.

1. Подписывайся также на structure.choch.<SYMBOL> и structure.bos.<SYMBOL>
   для всех ZT_SYMBOLS на 1h.
2. Поддерживай dict last_structure[symbol] = (kind, direction, time).
3. На signal с direction=long требуй последний structure event direction=up
   на 1h в течение последних 4 часов. Иначе [SKIP htf misaligned].
4. Аналогично для short.
```

## Promt 2: position sizing по balance

```
@bot.py @claude.md

Сейчас бот шлёт фиксированный ZT_AMOUNT_USD. Сделай чтобы он:

1. При старте дёргал `client.list_orders()` чтобы понять сколько ордеров
   уже открыто.
2. Считал baseline = ZT_TOTAL_BUDGET / ZT_MAX_CONCURRENT (новые env).
3. На каждый новый сигнал использовал `amount = baseline` если открытых
   ордеров < ZT_MAX_CONCURRENT, иначе [SKIP max_concurrent].
```

## Promt 3: telegram-нотификации

```
@bot.py @claude.md

Добавь Telegram-уведомления о fill/close:

1. ENV vars: TG_BOT_TOKEN, TG_CHAT_ID.
2. На action='filled' пиши: "✅ #42 BTCUSDT long filled @81015 qty=0.006"
3. На action='closed' пиши: "🎯 #42 BTCUSDT tp @81604 +1.96 USDT" (с эмодзи
   разным для tp/sl/manual).
4. Используй httpx (он уже в SDK deps как зависимость).
```

## Promt 4: dedup при рестарте

```
@bot.py @claude.md

Сейчас если бот рестартанёт и тот же signal придёт повторно — создастся
дубль ордера. Добавь file-based dedup:

1. Persist в seen_signals.json: dict[symbol_dir_entry_stop] = order_id
2. Перед place_order — проверять key в seen. Если есть — [SKIP duplicate].
3. После успешного place_order — сохранить key → order.id и flush на диск.
4. При старте — load seen_signals.json (если есть).

Ключ дедупа: f"{symbol}:{direction}:{entry}:{stop}" с округлением до 4 знаков.
```
