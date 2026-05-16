"""07 — Custom 3-drive detector built on top of structure-stream.

Демо-бот: показывает как из «сырых» структурных строительных блоков
(fractals + OB) собрать собственное правило сетапа — на примере
упрощённого 3-drive.

Поток работы:
  1. На старте — REST snapshot `/api/structure/snapshot` для каждой пары
     (через SDK `Client.get_structure_snapshot`). Получаем последние
     fractals → попадают в локальный state.
  2. Подписка на WS-каналы `structure.fractal.<TF>.<SYM>` для тех же пар.
     Каждый новый fractal append'ится в state.
  3. На каждом новом fractal — проверка 3-drive: ищем 3 последовательных
     одинаковых лейбла с прогрессией (3 LL ↓ для long-3-drive или
     3 HH ↑ для short-3-drive).
  4. Если паттерн найден — лог. Бот НЕ торгует, это образец.

Авторизация: тот же `externalSignalToken` что у других bot-template'ов.
Tier: free (structure.fractal.* — free channel).

Запуск:
    pip install -r requirements.txt
    cp .env.example .env  &&  отредактировать ZT_API_KEY
    python3.10 bot.py
"""

import asyncio
import logging
import os
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from zonetrade_sdk import Client, FractalEvent, SnapshotFractal


HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

WS_URL = os.environ.get("ZT_WS_URL", "ws://localhost:8087/external-signals")
API_BASE_URL = os.environ.get("ZT_API_BASE_URL", "http://localhost:8085")
TOKEN = os.environ.get("ZT_API_KEY", "").strip()
TF = os.environ.get("ZT_TF", "1m")
SYMBOLS_CSV = os.environ.get("ZT_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT")
WINDOW_BARS = int(os.environ.get("ZT_SNAPSHOT_WINDOW_BARS", "200"))
# Сколько последних фракталов держим в памяти на символ. Чем больше — тем
# дальше «видим» прогрессию, но 3-drive вряд ли нужен глубже 30.
KEEP_FRACTALS = 30
# Минимальный шаг прогрессии: каждая последующая LL должна быть НИЖЕ
# предыдущей хотя бы на N% от цены. 0 = просто строгое неравенство.
MIN_DRIVE_GAP_PCT = 0.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("3drive-bot")


# Локальный state: symbol → list of (label, price, timeMs), отсортированный
# по timeMs. Заполняется снепшотом, обновляется WS-событиями.
state: dict[str, list[tuple[str, float, int]]] = defaultdict(list)
# Чтобы не лоигровать один и тот же сетап повторно (3 последних LL
# не меняются между приходами фракталов отличного типа). Ключ —
# (symbol, last fractal idx, direction).
already_logged: set[tuple[str, int, str]] = set()


def _trim(symbol: str) -> None:
    if len(state[symbol]) > KEEP_FRACTALS:
        state[symbol] = state[symbol][-KEEP_FRACTALS:]


def detect_3drive(symbol: str, last_idx: int) -> None:
    """Простое правило: последние 3 fractals одного label с правильной
    монотонной прогрессией. Для бычьего setup'а (long) ищем 3 LL подряд
    с понижающейся ценой, для медвежьего (short) — 3 HH с растущей.

    В реальной 3-drive стратегии добавляют fibo-ретрейсменты между
    drives, валидацию через OB/FVG, RR-расчёт. Здесь — каркас."""
    items = state[symbol]
    if len(items) < 3:
        return
    # Тип последнего фрактала задаёт сторону которую ищем.
    last_label, last_price, _ = items[-1]
    if last_label not in {"LL", "HH"}:
        return
    same = [it for it in items[-10:] if it[0] == last_label]
    if len(same) < 3:
        return
    drives = same[-3:]
    p1, p2, p3 = drives[0][1], drives[1][1], drives[2][1]
    if last_label == "LL":
        # Long-3-drive: каждый следующий LL ниже предыдущего на ≥ gap_pct.
        gap1 = (p1 - p2) / p1
        gap2 = (p2 - p3) / p2
        if gap1 > MIN_DRIVE_GAP_PCT and gap2 > MIN_DRIVE_GAP_PCT:
            direction = "long"
        else:
            return
    else:  # HH
        gap1 = (p2 - p1) / p1
        gap2 = (p3 - p2) / p2
        if gap1 > MIN_DRIVE_GAP_PCT and gap2 > MIN_DRIVE_GAP_PCT:
            direction = "short"
        else:
            return
    key = (symbol, last_idx, direction)
    if key in already_logged:
        return
    already_logged.add(key)
    drive_prices = [f"{d[1]:.4g}" for d in drives]
    log.info(
        "★ 3-DRIVE %s %s detected on %s — drives %s → entry near last drive %s",
        direction.upper(), last_label, symbol, drive_prices, drive_prices[-1],
    )


async def seed_from_snapshot(client: Client, symbols: list[str]) -> None:
    for sym in symbols:
        try:
            snap = await client.get_structure_snapshot(
                sym, tf=TF, window_bars=WINDOW_BARS,
            )
        except Exception as e:
            log.warning("snapshot %s failed: %s", sym, e)
            continue
        for fr in snap.fractals:
            state[sym].append((fr.label, fr.price, fr.timeMs))
        state[sym].sort(key=lambda t: t[2])
        _trim(sym)
        log.info(
            "seeded %s: %d fractals (last %s @ %s)", sym, len(state[sym]),
            state[sym][-1][0] if state[sym] else "—",
            state[sym][-1][1] if state[sym] else "—",
        )
        # Сразу проверяем — может уже на snapshot'е виден готовый 3-drive.
        last_idx = snap.fractals[-1].idx if snap.fractals else -1
        if last_idx >= 0:
            detect_3drive(sym, last_idx)


async def main() -> None:
    if not TOKEN:
        log.error("ZT_API_KEY не задан в .env")
        return
    symbols = [s.strip().upper() for s in SYMBOLS_CSV.split(",") if s.strip()]
    log.info("symbols=%s tf=%s", symbols, TF)

    client = Client(api_key=TOKEN, base_url=WS_URL, api_base_url=API_BASE_URL)

    @client.on("structure")
    async def on_structure(ev):
        # Маршрутизация в SDK route'ит `structure.fractal.*` в FractalEvent,
        # `structure.(bos|choch).*` — в StructureEvent. Здесь обрабатываем
        # только fractal — для 3-drive остальное не нужно.
        if not isinstance(ev, FractalEvent):
            return
        state[ev.symbol].append((ev.type, ev.price, ev.timeMs))
        state[ev.symbol].sort(key=lambda t: t[2])
        _trim(ev.symbol)
        log.info("fractal %s %s @ %s", ev.symbol, ev.type, ev.price)
        detect_3drive(ev.symbol, ev.idx)

    await seed_from_snapshot(client, symbols)

    channels = [f"structure.fractal.{TF}.{sym}" for sym in symbols]
    log.info("subscribing to %d channels", len(channels))
    try:
        await client.run(subscribe=channels)
    except KeyboardInterrupt:
        log.info("bye")
    finally:
        await client.stop()
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
