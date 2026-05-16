# Zonetrade Bot Templates

Готовые Python-боты на базе [`zonetrade-sdk`](https://github.com/zonetradeapp/zonetrade-sdk):
паттерны от простого «print all events» до custom-детектора и paper-trading'a.
Цель — `git clone`, заполнить `.env`, `python bot.py` — и ты в WS-стриме.

## Шаблоны

| # | Имя | Сложность | Что показывает |
|---|-----|-----------|----------------|
| 01 | [`print-events`](./01-print-events) | beginner | Минимальный bot: коннект к WS → печать каждого события. Для debug + знакомства с потоком. |
| 02 | [`multi-symbol-aggregator`](./02-multi-symbol-aggregator) | intermediate | Слушает 5+ символов параллельно, агрегирует события в Redis. Шаблон под dashboard'ы и alerting. |
| 03 | [`auto-trader`](./03-auto-trader) ⭐ | intermediate | Сигнал → paper-ордер на виртуальной бирже Zonetrade → fill/PnL обратно. **Рекомендован для старта** — без риска реальных денег. |
| 04 | [`custom-3drive-from-fractals`](./04-custom-3drive-from-fractals) | advanced | Свой 3-drive детектор поверх `structure-snapshot` + fractal-стрима. Пример того, как строить кастомные сигналы из base-event'ов. |

## Quickstart

```bash
# 1. Установи SDK
pip install git+https://github.com/zonetradeapp/zonetrade-sdk

# 2. Клонируй templates
git clone https://github.com/zonetradeapp/bot-templates
cd bot-templates/03-auto-trader

# 3. Заполни .env (API-ключ берёшь на https://zonetrade.app/integration/api-keys)
cp .env.example .env
$EDITOR .env

# 4. Запусти
pip install -r requirements.txt
python bot.py
```

## Tier-доступ

Каждый шаблон работает на определённых WS-каналах. Они открываются по
tier-подписке (см. `https://zonetrade.app/integration/pricing`):

| Tier | Что доступно |
|------|--------------|
| **Free** | 3-drive без HTF фильтра, 1m. Базовый стрим (`bar.*`, `zone.*`, `structure.*`). |
| **Starter** | + 3-drive с HTF фильтром, + структурный поток (FVG, OB, CHoCH, BoS, fractals). |
| **Pro** | + Trap-Flip премиум-сигналы. |

## SDK + reference

- SDK: <https://github.com/zonetradeapp/zonetrade-sdk>
- AI-агент гайд (для Claude/Cursor): [`claude.md`](https://github.com/zonetradeapp/zonetrade-sdk/blob/main/claude.md)
- Pricing: <https://zonetrade.app/integration/pricing>

## License

MIT (см. [LICENSE](./LICENSE))
