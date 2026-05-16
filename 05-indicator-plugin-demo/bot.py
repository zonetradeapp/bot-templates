"""08 — FractalsPlugin demo.

Минимальный бот, который через SDK подключает официальный FractalsPlugin.
Плагин на старте дёргает REST snapshot, рисует исторические фракталы как
labels на чарте у юзера, и подписывается на live-обновления.

Запуск:
    cd bot-templates/08-fractals-plugin-demo
    cp .env.example .env  &&  заполни ZT_API_KEY
    pip install -r requirements.txt
    python3.10 bot.py
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from zonetrade_sdk import Client
from zonetrade_sdk.plugins.fractals import FractalsPlugin


HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")

WS_URL = os.environ.get("ZT_WS_URL", "ws://localhost:8087/external-signals")
API_BASE_URL = os.environ.get("ZT_API_BASE_URL", "http://localhost:8085")
TOKEN = os.environ.get("ZT_API_KEY", "").strip()
SYMBOLS_CSV = os.environ.get("ZT_SYMBOLS", "BTCUSDT")
TF = os.environ.get("ZT_TF", "1m")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fractals-demo")


async def main() -> None:
    if not TOKEN:
        log.error("ZT_API_KEY не задан в .env")
        return
    symbols = [s.strip().upper() for s in SYMBOLS_CSV.split(",") if s.strip()]
    log.info("symbols=%s tf=%s", symbols, TF)

    client = Client(api_key=TOKEN, base_url=WS_URL, api_base_url=API_BASE_URL)
    client.use(FractalsPlugin(symbols=symbols, tf=TF, limit=200, ttl_sec=3600))

    try:
        await client.run()
    except KeyboardInterrupt:
        log.info("bye")
    finally:
        # client.stop() → plugin.on_unload() → render-objects удалятся.
        await client.stop()
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
