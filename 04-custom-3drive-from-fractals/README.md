# 07 — Custom 3-drive detector (snapshot + structure stream)

Демо-бот: как из «сырых» структурных строительных блоков (`fractals`)
самостоятельно собрать сетап-логику — на примере упрощённого 3-drive.

## Поток работы

1. **REST snapshot** через SDK `Client.get_structure_snapshot(symbol, tf)`
   — получаем последние N закрытых свечей и считанные на них fractals
   (HH/HL/LH/LL/SH/SL). Засеваем локальный state.
2. **WS subscribe** на `structure.fractal.<TF>.<SYMBOL>` для тех же
   пар. Каждый новый фрактал приходит как `FractalEvent`, append'им
   в state.
3. **Детектор 3-drive** на каждом новом фрактале — ищем 3 последних
   одного label (LL для long-3-drive ↓ или HH для short ↑) и
   проверяем монотонную прогрессию. Если найдено — лог.

Бот **не торгует** — это образец паттерна «как работать с каналами».
Реальный 3-drive дополнительно валидирует:
- fibo-ретрейсменты между drives (0.618/0.786);
- размер каждого drive ≥ N% от прошлого;
- POI-фильтр (entry внутри OB/FVG из snapshot'а);
- HTF-тренд (можно подписаться на `structure.bos.4h.<SYM>` для контекста);
- стоп/тейки от geometry of drives.

## Зачем snapshot если есть WS

WS отдаёт только **новые** events после подключения. Без snapshot'а
бот ждал бы первый fractal — на 1m это 1-2 минуты, на 4h это часы.
Snapshot-then-stream — стандартный паттерн (Binance, Bybit делают
так же для стаканов).

## Запуск

```bash
pip install -r requirements.txt
cp .env.example .env  # заполни ZT_API_KEY
python3.10 bot.py
```

## Конфигурация (.env)

| var | default | назначение |
|---|---|---|
| `ZT_API_KEY` | — | externalSignalToken юзера |
| `ZT_WS_URL` | `ws://localhost:8087/external-signals` | WS endpoint |
| `ZT_API_BASE_URL` | `http://localhost:8085` | REST origin (snapshot endpoint) |
| `ZT_SYMBOLS` | `BTCUSDT,ETHUSDT,SOLUSDT` | CSV пар |
| `ZT_TF` | `1m` | TF свечей и канала |
| `ZT_SNAPSHOT_WINDOW_BARS` | `200` | сколько закрытых свечей в snapshot'е |

## Tier

Каналы `structure.fractal.*` и REST snapshot — **free tier**.
Подходит и для `structure.bos.*`, `structure.choch.*`, `zone.ob.*`
(см. SDK модели `StructureEvent`, `ObZoneEvent`) — расширь handler
если хочешь полную SMC-картину.
