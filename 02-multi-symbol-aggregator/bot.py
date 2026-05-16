"""03 multi-symbol aggregator.

Бот подписывается на 3-drive setups + bars по 5+ символам, агрегирует
состояние per-symbol (last bar, recent setups, recent zones), сохраняет
в Redis. Готовая база для:
  - ML feature pipeline (бар-by-бар features → training set)
  - Аналитика (топ setups by symbol, time-of-day patterns)
  - Cross-symbol corr filter (входим в LONG BTC только если ETH тоже long-bias)

Tier: Starter ($25) для signal.three-drive-v11.* ИЛИ Free если ТОЛЬКО raw.
"""

import asyncio
import json
import logging
import os
import sys
from collections import deque
from datetime import datetime

import redis.asyncio as aredis

from zonetrade_sdk import Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("aggregator")

SYMBOLS = os.environ.get("SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT").split(",")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
TF_PRIMARY = os.environ.get("TF_PRIMARY", "1m")  # для bars


class SymbolState:
    """Per-symbol state. Last bar, recent setups, recent zones."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.last_bar = None
        self.recent_setups = deque(maxlen=10)  # последние 10 3-drive pivot'ов
        self.recent_zones = deque(maxlen=20)   # последние 20 zone-event'ов
        self.bar_count = 0  # сколько баров получено


async def main() -> None:
    api_key = os.environ.get("ZT_API_KEY")
    if not api_key:
        print("ERROR: set ZT_API_KEY")
        sys.exit(1)

    redis = aredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await redis.ping()
        logger.info(f"redis connected: {REDIS_URL}")
    except Exception as e:
        logger.warning(f"redis unavailable ({e}), running without persistence")
        redis = None

    state: dict[str, SymbolState] = {s: SymbolState(s) for s in SYMBOLS}
    client = Client(api_key=api_key)

    @client.on("bar")
    async def on_bar(bar):
        if bar.tf != TF_PRIMARY:
            return
        s = state.get(bar.symbol)
        if not s:
            return
        s.last_bar = bar
        s.bar_count += 1
        if redis:
            await redis.set(
                f"agg:bar:{bar.symbol}:{bar.tf}",
                bar.model_dump_json(),
                ex=3600,
            )

    @client.on("setup")
    async def on_setup(setup):
        s = state.get(setup.symbol)
        if not s:
            return
        s.recent_setups.append({
            "direction": setup.direction,
            "entry": setup.confirmPrice,
            "time": setup.confirmTime,
            "drives": setup.drives,
        })
        if redis:
            await redis.lpush(f"agg:setups:{setup.symbol}", setup.model_dump_json())
            await redis.ltrim(f"agg:setups:{setup.symbol}", 0, 49)
        logger.info(
            f"[setup] {setup.symbol} {setup.direction} entry={setup.confirmPrice} "
            f"(total {len(s.recent_setups)})"
        )

    @client.on("zone")
    async def on_zone(zone):
        s = state.get(zone.symbol)
        if not s:
            return
        s.recent_zones.append({
            "kind": type(zone).__name__,
            "side": zone.side,
            "top": zone.top,
            "bottom": zone.bottom,
            "fillPct": zone.fillPct,
        })

    async def print_summary():
        """Каждые 60 сек печатает per-symbol summary."""
        while True:
            await asyncio.sleep(60)
            logger.info("─" * 50)
            for sym, s in state.items():
                up = sum(1 for x in s.recent_setups if x["direction"] == "long")
                dn = sum(1 for x in s.recent_setups if x["direction"] == "short")
                logger.info(
                    f"{sym}: bars={s.bar_count} setups[{up}↑/{dn}↓] zones={len(s.recent_zones)}"
                )

    # Подписки.
    subs = []
    for sym in SYMBOLS:
        subs.append(f"bar.{TF_PRIMARY}.{sym}")
        subs.append(f"setup.three-drive-raw.{sym}")
        subs.append(f"zone.fvg.{sym}")
        subs.append(f"zone.ob.{sym}")

    logger.info(f"watching {len(SYMBOLS)} symbols, {len(subs)} channels")

    summary_task = asyncio.create_task(print_summary())
    try:
        await client.run(subscribe=subs)
    finally:
        summary_task.cancel()
        if redis:
            await redis.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
