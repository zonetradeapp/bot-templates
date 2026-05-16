"""04 auto-trader — paper-trading на нашей виртуальной бирже.

Слушает signals от Zonetrade, на каждый отправляет paper-ордер через
`/api/v1/orders`. Параллельно подписан на `user.<id>.order` чтобы видеть
push-уведомления о fill/close/PnL без polling'а REST API.

Это **не реальная торговля** на бирже — ордера живут на нашем backend'е,
матчатся против Binance spot price (cron `app:check-orders` /
`app:check-trades`). PnL начисляется в виртуальные «coins» юзера.

Use case: тестировать стратегию на чистой инфре без риска реальных
денег. Когда будешь готов идти на mainnet — см. template 02 (Binance
bridge) который то же самое, но через python-binance.

Tier: Free для `three-drive-v11` raw, Starter для V11, Pro для trap-flip.
"""

import asyncio
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from zonetrade_sdk import Client, OrderError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("auto-trader")

# ENV — короткий список, всё опционально кроме API key.
# ZT_SYMBOLS=auto (или пустой) — берём whitelist из настроек юзера
# (User.signalSymbols, тот же что фильтрует уведомления). Иначе CSV-override.
_RAW_SYMBOLS = os.environ.get("ZT_SYMBOLS", "auto").strip()
SYMBOLS_AUTO = _RAW_SYMBOLS.lower() in ("", "auto")
SYMBOLS = [] if SYMBOLS_AUTO else [s.strip().upper() for s in _RAW_SYMBOLS.split(",") if s.strip()]
# Поддерживаемые стратегии:
#   three-drive-raw — free tier, без HTF-фильтра (setup.three-drive-raw.<SYMBOL>)
#   three-drive-v11 — starter tier, с HTF-фильтром (signal.three-drive-v11.<SYMBOL>)
#   trap-flip       — pro tier (signal.trap-flip.<SYMBOL>)
STRATEGY = os.environ.get("ZT_STRATEGY", "three-drive-v11")
# Список TF для подписки на сигналы. CSV, default '1m'. Каналы строятся как
# <kind>.<strategy>.<tf>.<SYMBOL>, по одному на каждый TF.
TIMEFRAMES = [tf.strip() for tf in os.environ.get("ZT_TIMEFRAMES", "1m").split(",") if tf.strip()]
# Sizing: три режима, приоритет сверху-вниз:
#   - ZT_RISK_PERCENT=1   — risk-based: убыток на SL = N% balance. Считаем
#                            qty = risk_usd / |entry-stop|, отправляем reverse
#                            amount = qty × entry / LEVERAGE чтобы backend
#                            (применяющий leverage 5×) дал нужный qty.
#   - ZT_AMOUNT_PERCENT=1 — margin-based: N% balance как margin.
#   - ZT_AMOUNT_USD=100   — fallback fixed margin.
AMOUNT_USD = float(os.environ.get("ZT_AMOUNT_USD", "100"))
_pct_raw = os.environ.get("ZT_AMOUNT_PERCENT", "").strip()
AMOUNT_PERCENT: float | None = float(_pct_raw) if _pct_raw else None
_risk_raw = os.environ.get("ZT_RISK_PERCENT", "").strip()
RISK_PERCENT: float | None = float(_risk_raw) if _risk_raw else None
LEVERAGE = float(os.environ.get("ZT_LEVERAGE", "5"))  # mirror OrderService.php::LEVERAGE
MIN_RR = float(os.environ.get("ZT_MIN_RR", "1.5"))
DRY_RUN = os.environ.get("ZT_DRY_RUN", "0") == "1"

# Маппинг стратегии → префикс канала + имя event handler'а в SDK.
# SDK диспатчит по event-полю payload'а: signal.* → "signal", setup.* → "setup".
_STRATEGY_CHANNEL = {
    "three-drive-raw":  ("setup",  "setup.three-drive-raw"),
    "three-drive-v11":  ("signal", "signal.three-drive-v11"),
    "trap-flip":        ("signal", "signal.trap-flip"),
}


async def main() -> None:
    api_key = os.environ.get("ZT_API_KEY")
    if not api_key:
        print("ERROR: set ZT_API_KEY env var (get key at https://zonetrade.app/bot/api-keys)")
        sys.exit(1)

    # ZT_BASE_URL — WS endpoint (override prod default для dev/staging).
    # ZT_API_ORDERS_URL — origin REST API `/api/v1/orders/*` (без пути).
    # Если ZT_API_ORDERS_URL не задан, SDK выведет его из ZT_BASE_URL
    # (wss://host/... → https://host). В local dev WS и REST живут на
    # разных портах, так что нужно явно указать оба.
    base_url = os.environ.get("ZT_BASE_URL")
    api_orders_url = os.environ.get("ZT_API_ORDERS_URL")
    kwargs: dict = {"api_key": api_key}
    if base_url: kwargs["base_url"] = base_url
    if api_orders_url: kwargs["api_base_url"] = api_orders_url
    client = Client(**kwargs)

    if STRATEGY not in _STRATEGY_CHANNEL:
        print(f"ERROR: unknown ZT_STRATEGY={STRATEGY}. Supported: {list(_STRATEGY_CHANNEL)}")
        sys.exit(1)
    sdk_event, channel_prefix = _STRATEGY_CHANNEL[STRATEGY]

    async def handle_setup(sig) -> None:
        """Унифицированный обработчик и signal-event'ов, и setup-event'ов.

        signal.three-drive-v11 / signal.trap-flip приходят с готовой
        стратегией в `sig.strategy`. setup.three-drive-raw приходит с
        `strategy='three-drive'` + `version='raw'` — фильтруем по
        comparison целевой стратегии.
        """
        is_raw = (sig.strategy == "three-drive" and getattr(sig, "version", None) == "raw")
        strategy_id = "three-drive-raw" if is_raw else sig.strategy
        if strategy_id != STRATEGY:
            return
        # Для raw entry/stop/rr опциональные — если паблишер старого
        # формата, поля будут None. На geom-валидацию backend всё равно
        # вернёт ошибку, но лучше отфильтровать заранее.
        entry = getattr(sig, "entry", None)
        stop = getattr(sig, "stop", None)
        tp1 = getattr(sig, "tp1", None)
        if entry is None or stop is None or tp1 is None:
            logger.info(f"[SKIP no-fields] {sig.symbol} {sig.direction} — payload missing entry/stop/tp1")
            return
        rr = getattr(sig, "rr", None)
        if rr is None:
            # raw-payload не несёт rr — считаем из tp1/entry/stop сами.
            risk = abs(entry - stop)
            reward = abs(tp1 - entry)
            rr = (reward / risk) if risk > 0 else None
        if rr is not None and rr < MIN_RR:
            logger.info(f"[SKIP] {sig.symbol} {sig.direction} RR={rr:.2f} < {MIN_RR}")
            return

        rr_str = f"RR={rr:.2f}" if rr is not None else "RR=?"
        msg = (f"{sig.symbol} {sig.direction} @{entry} SL={stop} "
               f"TP1={tp1} TP2={getattr(sig, 'tp2', None)} TP3={getattr(sig, 'tp3', None)} {rr_str}")
        # Percent/risk-mode: пытаемся свежий balance через REST. На fail —
        # cached из hello (`client.coins`), на zero cached — fixed.
        if RISK_PERCENT is not None or AMOUNT_PERCENT is not None:
            try:
                acc = await client.get_account()
                coins = acc.coins
            except Exception as e:
                coins = client.coins
                logger.warning(f"get_account failed ({e}), using cached coins={coins}")
        else:
            coins = 0
        if RISK_PERCENT is not None and coins > 0 and entry != stop:
            risk_usd = coins * RISK_PERCENT / 100
            target_qty = risk_usd / abs(entry - stop)
            amount = round(target_qty * entry / LEVERAGE, 2)
            if amount <= 0:
                logger.warning(f"[risk-based zero] coins={coins} → fallback ${AMOUNT_USD}")
                amount = AMOUNT_USD
        elif AMOUNT_PERCENT is not None and coins > 0:
            amount = round(coins * AMOUNT_PERCENT / 100, 2)
        elif AMOUNT_PERCENT is not None:
            logger.warning(f"[zero balance] cached coins=0 → fallback to ${AMOUNT_USD}")
            amount = AMOUNT_USD
        else:
            amount = AMOUNT_USD

        if DRY_RUN:
            logger.info(f"[DRY] would place: {msg} amount=${amount}")
            return

        try:
            order = await client.place_order(
                symbol=sig.symbol,
                side=sig.direction,
                entry=entry,
                stop=stop,
                tp1=tp1,
                tp2=getattr(sig, "tp2", None),
                tp3=getattr(sig, "tp3", None),
                amount=amount,
            )
            logger.info(f"[PLACED #{order.id}] {msg} type={order.type} qty={order.quantity:.6f}")
        except OrderError as e:
            # 'insufficient_funds' / 'geom_*' / 'forbidden' и т.д. см.
            # docs/description/18-bot-platform/06-orders-v1-implemented.md
            logger.warning(f"[REJECT {e.code}] {msg} (http {e.status})")

    client.on(sdk_event)(handle_setup)

    @client.on("order")
    async def on_order(ev):
        # Push-event от `user.<id>.order` канала: fill/close/cancel/invalidate.
        if ev.action == "filled":
            logger.info(f"[FILLED #{ev.orderId}] {ev.symbol} @{ev.entryPrice} qty={ev.quantity}")
        elif ev.action == "closed":
            pnl_str = f"PnL={ev.pnl:+.2f}" if ev.pnl is not None else ""
            reason = ev.reason or "?"
            logger.info(f"[CLOSED #{ev.orderId}] {ev.symbol} {reason} @{ev.exitPrice} {pnl_str}")
        elif ev.action == "invalidated":
            logger.info(f"[INVALIDATED #{ev.orderId}] {ev.symbol} — setup стал невалидным")
        else:
            logger.info(f"[{ev.action.upper()} #{ev.orderId}] {ev.symbol}")

    # Если SYMBOLS_AUTO — список приходит из hello (User.signalSymbols),
    # значит подписаться сразу не можем, делаем это в фоне после hello.
    # Иначе SYMBOLS уже задан из env → subscribe на старте.
    # Subscribe-list: <kind>.<strategy>.<tf>.<SYMBOL> per (tf × symbol).
    subscribe_now = [] if SYMBOLS_AUTO else [
        f"{channel_prefix}.{tf}.{s}" for s in SYMBOLS for tf in TIMEFRAMES
    ]
    mode = "DRY-RUN" if DRY_RUN else "LIVE (paper)"
    src = "auto (User.signalSymbols)" if SYMBOLS_AUTO else f"env={SYMBOLS}"
    if RISK_PERCENT is not None:
        amt_desc = f"risk {RISK_PERCENT}% of coins (lev={LEVERAGE}×)"
    elif AMOUNT_PERCENT is not None:
        amt_desc = f"{AMOUNT_PERCENT}% of coins (margin)"
    else:
        amt_desc = f"${AMOUNT_USD} (fixed margin)"
    logger.info(f"mode={mode} strategy={STRATEGY} tfs={TIMEFRAMES} symbols={src} amount={amt_desc} min_rr={MIN_RR}")

    async def _post_hello_setup() -> None:
        # Resolved-список ждёт `user_id` (=hello). subscribe_orders сам ждёт
        # внутри — переиспользуем тот же пред-условие здесь.
        for _ in range(50):
            if client.user_id is not None: break
            await asyncio.sleep(0.1)
        # Стартовый balance из hello (cached `client.coins`) — без extra REST.
        # После wins/losses на backend coins меняются, для свежей цифры в
        # percent-mode handle_setup сам вызовет get_account().
        if RISK_PERCENT is not None:
            risk_usd = round(client.coins * RISK_PERCENT / 100, 2)
            logger.info(f"[balance] coins={client.coins} → risk=${risk_usd} per trade ({RISK_PERCENT}%, lev={LEVERAGE}×)")
        elif AMOUNT_PERCENT is not None:
            preview = round(client.coins * AMOUNT_PERCENT / 100, 2)
            logger.info(f"[balance] coins={client.coins} → amount=${preview} ({AMOUNT_PERCENT}%)")
        else:
            logger.info(f"[balance] coins={client.coins} → amount=${AMOUNT_USD} (fixed)")
        if SYMBOLS_AUTO:
            resolved = client.resolved_signal_symbols()
            channels = [f"{channel_prefix}.{tf}.{s}" for s in resolved for tf in TIMEFRAMES]
            logger.info(f"resolved symbols from User.signalSymbols: {resolved} × tfs={TIMEFRAMES}")
            await client.subscribe(channels)
        try:
            await client.subscribe_orders()
            logger.info("subscribed to order events")
        except Exception as e:
            logger.warning(f"subscribe_orders failed: {e}")

    asyncio.create_task(_post_hello_setup())
    await client.run(subscribe=subscribe_now)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
