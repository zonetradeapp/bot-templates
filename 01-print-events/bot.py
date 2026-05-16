"""01 print-events — самый минимальный бот.

Подключается к Zonetrade WS, подписывается на несколько каналов, печатает
каждое полученное событие. Полезен чтобы проверить что:
  - API key работает
  - SDK установился корректно
  - WS-сервер достижим

Tier: Free.
"""

import asyncio
import logging
import os
import sys

# Опционально подгружаем .env (если установлен python-dotenv).
try:
    from dotenv import load_dotenv
    # ищем .env в текущей папке + в папке скрипта (универсально для
    # запуска и из bot-templates/, и из 01-print-events/)
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

from zonetrade_sdk import Client

# SDK info-logs (connected, subscribed, etc.) → stdout.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


async def main() -> None:
    api_key = os.environ.get("ZT_API_KEY")
    if not api_key:
        print("ERROR: set ZT_API_KEY env var (get key at https://zonetrade.app/bot/api-keys)")
        sys.exit(1)

    # ZT_BASE_URL опционально — для локальной разработки.
    # Production default: wss://zonetrade.app/external-signals.
    base_url = os.environ.get("ZT_BASE_URL")
    client = Client(api_key=api_key, base_url=base_url) if base_url else Client(api_key=api_key)

    @client.on("hello")
    async def on_hello(msg):
        settings = msg.get("settings", {})
        tier = settings.get("subscriptionTier", "free")
        print(f"[hello] user={msg.get('userId')} tier={tier}")

    @client.on("bar")
    async def on_bar(bar):
        print(f"[bar]    {bar.symbol} {bar.tf} close={bar.close} vol={bar.volume:.2f}")

    @client.on("zone")
    async def on_zone(zone):
        print(f"[zone]   {zone.symbol} {type(zone).__name__} {zone.side} "
              f"top={zone.top} bot={zone.bottom} fill={zone.fillPct:.2f}")

    @client.on("structure")
    async def on_structure(ev):
        print(f"[struct] {ev.symbol} {ev.kind} {ev.direction} price={ev.price}")

    @client.on("setup")
    async def on_setup(setup):
        print(f"[setup]  {setup.symbol} {setup.strategy}-{setup.version} "
              f"{setup.direction} entry={setup.confirmPrice}")

    print("Connecting to Zonetrade WS...")
    await client.run(subscribe=[
        # Все базовые каналы — free tier.
        "bar.1m.BTCUSDT",
        "bar.1m.ETHUSDT",
        "zone.fvg.BTCUSDT",
        "zone.ob.BTCUSDT",
        "structure.choch.BTCUSDT",
        "structure.bos.BTCUSDT",
        "setup.three-drive-raw.BTCUSDT",
    ])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
