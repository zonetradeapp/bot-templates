# 05 — Indicator Plugin demo (draw on the chart from a bot)

Run this bot on your laptop → see **SMC fractal markers appear on your chart at [zonetrade.app](https://zonetrade.app)** (HH/HL/LH/LL/SH/SL). The bot doesn't trade — it **draws**.

This is the "bot as indicator" pattern: your Python code computes something (fractals, FVG, order blocks, patterns) and uses the SDK to **publish visual primitives onto your own chart**. No frontend code — Python only.

## What you can draw from a bot

The SDK exposes five primitives through the `render-objects` API. Every object appears on the chart of the user who owns the API key.

| Method | What it draws | When to use |
|---|---|---|
| `client.render_marker(price, time, color, label?, radius?)` | A dot at `(time, price)` with an optional label | fractals, POIs, trigger events |
| `client.render_line(price, color, dash?, label?)` | A horizontal line through the entire chart | support/resistance levels, liquidity |
| `client.render_zone(top, bottom, color, label?)` | A full-width rectangle between two prices | volatility zones, equilibrium |
| `client.render_label(price, time, text, color)` | Text anchored at `(time, price)` | event annotations |
| `client.render_position(side, entry, stop, take, time, end_time)` | **Bounded** trade-style visual: risk/profit zones, entry/SL/TP lines, LONG/SHORT badge | detected setup, paper-style overlay |

**Current API v1 limits:**
- Sloped lines are not supported — only horizontal.
- `zone` spans the full visible time. For bounded rectangles use `render_position`.

## What this bot does

1. Connects via WebSocket using your `externalSignalToken`
2. Loads the official **`FractalsPlugin`** from `zonetrade_sdk.plugins.fractals`
3. On startup the plugin:
   - Pulls 200 candles from Bybit for each symbol in `ZT_SYMBOLS`
   - Runs a Williams N-bar fractal detector
   - Calls `client.render_marker(...)` for each fractal, with a color based on its type (HH/HL/LH/LL/SH/SL)
4. Markers are pushed through the WS render-objects channel and show up on your chart
5. On `client.stop()` the plugin auto-removes everything it created (cleanup)

## Step 1 — get an API key

1. Go to [zonetrade.app](https://zonetrade.app) and log in
2. Open **Settings → Integration → API Keys**
3. Copy the `externalSignalToken` — this is your personal bot token

The same token is used for all render-objects: they will appear **only on your own chart**, scoped to the user who owns the token.

## Step 2 — clone the template and install dependencies

```bash
git clone https://github.com/zonetradeapp/bot-templates
cd bot-templates/05-indicator-plugin-demo

cp .env.example .env
$EDITOR .env                          # paste your ZT_API_KEY

pip install -r requirements.txt       # pulls zonetrade-sdk + plugin
```

## Step 3 — fill in `.env`

```env
ZT_API_KEY=your-externalSignalToken
ZT_WS_URL=wss://zonetrade.app/external-signals       # prod (or ws://localhost for dev)
ZT_API_BASE_URL=https://zonetrade.app
ZT_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT                   # CSV or `*` for all watched pairs
ZT_TF=1m                                             # candle/fractal timeframe
```

## Step 4 — run it

```bash
python bot.py
```

Expected log output:
```
17:23:01 [INFO] zonetrade_sdk: connected to wss://zonetrade.app/external-signals
17:23:01 [INFO] zonetrade_sdk: hello user=42 settings={...}
17:23:02 [INFO] zonetrade_sdk.plugins.fractals: [fractals] BTCUSDT/1m: 200 candles → 38 fractals (N=2)
17:23:03 [INFO] zonetrade_sdk.plugins.fractals: [fractals] ETHUSDT/1m: 200 candles → 42 fractals (N=2)
...
```

The bot keeps running until you press Ctrl+C.

## Step 5 — open the chart in your browser

1. Open [zonetrade.app](https://zonetrade.app) **logged into the same account**
2. Switch to one of the pairs the bot is watching (e.g. BTCUSDT)
3. Set the timeframe to `1m` (or whatever you set in `ZT_TF`)
4. You'll see **markers** labelled HH/HL/LH/LL/SH/SL — those are your fractals, painted by the bot

> If nothing shows up — open DevTools → Console and check for WS connection errors. Also look at the bot logs for `403` / `auth failed` (means the token is invalid).

## Step 6 — stop the bot (cleanup)

```
^C
17:25:14 [INFO] fractals-demo: bye
```

On `client.stop()` the SDK calls `plugin.on_unload()` → the plugin **deletes every render-object it created** via `DELETE /api/v1/render-objects/<id>`. Your chart is clean again.

If you want markers to **survive after the bot exits** — every render-object has a `ttl` (default 1 hour, max 7 days). They expire automatically on the server.

## Customising the plugin

In `bot.py`:
```python
client.use(FractalsPlugin(symbols=symbols, tf=TF, limit=200, ttl_sec=3600))
```

Available parameters:

| param | default | what it changes |
|---|---|---|
| `symbols` | required | CSV of pairs, or `['*']` to use all of the user's watched symbols |
| `tf` | `'1m'` | timeframe of candles and fractals |
| `n` | `2` | fractal width (1 = 3-bar, 2 = 5-bar, 3 = 7-bar) |
| `respect_inside_candles` | `True` | skip inside-bars when searching for swings |
| `limit` | `200` | how many candles to pull from Bybit (max 1000) |
| `ttl_sec` | `3600` | TTL of markers on the chart, in seconds |

Tweak and restart — you'll see the difference immediately.

## Writing your own plugin

Every official plugin lives inside the SDK as `zonetrade_sdk.plugins.<slug>`. Structure:

```
zonetrade_sdk/plugins/myob/
├── __init__.py          # exports MyObPlugin
├── compute.py           # pure algorithm (usable standalone)
└── plugin_class.py      # class MyObPlugin(Plugin) with on_init / on_event
```

Minimal plugin:

```python
from zonetrade_sdk import Plugin

class MyObPlugin(Plugin):
    name = "my_ob"

    def __init__(self, symbols, tf="1m"):
        super().__init__()
        self.symbols = symbols
        self.tf = tf

    async def on_init(self):
        for sym in self.symbols:
            # your own logic — detect OB / FVG / any pattern
            zones = my_detector(sym, self.tf)
            for zone in zones:
                await self.render_zone(
                    symbol=sym, tf=self.tf,
                    top=zone.top, bottom=zone.bottom,
                    color="rgba(34,197,94,0.2)",
                    label="OB",
                )
```

Methods exposed by the `Plugin` base class:
- `await self.render_marker(...)`, `render_line(...)`, `render_zone(...)`, `render_label(...)`, `render_position(...)`
- `await self.cleanup_render()` — delete everything the plugin drew (called automatically on unload)

Then in the bot:
```python
client.use(MyObPlugin(symbols=['BTCUSDT'], tf='15m'))
await client.run()
```

## Third-party plugins as pip packages

Your plugin can be published as a **standalone pip package** (community):

```bash
pip install zonetrade-sdk zonetrade-plugin-myob
```
```python
from zonetrade_sdk import Client
from zonetrade_plugin_myob import MyObPlugin

client.use(MyObPlugin(...))
```

The contract is inheritance from `zonetrade_sdk.Plugin`. The SDK doesn't distinguish "official" plugins from third-party ones — anything that subclasses `Plugin` plugs in through `client.use()`.

## Reference

- SDK: <https://github.com/zonetradeapp/zonetrade-sdk>
- Render-objects API: see the `Plugin` base class in the SDK
- Built-in plugins: `zonetrade_sdk.plugins.fractals`, `zonetrade_sdk.plugins.three_drive`
