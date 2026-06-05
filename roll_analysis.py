import csv
import math
import random
from enum import Enum
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# -----------------------------------------------------------------------------
# SECTION 1 — Enum & OrderBook Core
# -----------------------------------------------------------------------------

class EventType(Enum):
    NEW = 'new'
    CANCEL = 'cancel'
    MODIFY = 'modify'
    TRADE = 'trade'

class OrderBook:
    def __init__(self):
        self.bids = {}
        self.asks = {}
        self.orders = {}

    def _make_order(self, side, price, size):
        return {'side': side, 'price': price, 'size': size}
    
    def _process_events(self, event):
        if event['event_type'] == EventType.NEW.value:
            self._process_new_event(event)
        elif event['event_type'] == EventType.MODIFY.value:
            self._process_modify_event(event)
        elif event['event_type'] == EventType.CANCEL.value:
            self._process_cancel_event(event)
        elif event['event_type'] == EventType.TRADE.value:
            self._process_trade_event(event)

    def _process_new_event(self, event):
        if event['order_id'] in self.orders:
            raise ValueError("duplicate order")
        else:
            self.orders[event['order_id']] = self._make_order(event['side'], event['price'], event['size'])
            if event['side'] == 'bid':
                self.bids[event['price']] = self.bids.get(event['price'], 0) + event['size']
            else:
                self.asks[event['price']] = self.asks.get(event['price'], 0) + event['size']
    
    def _process_modify_event(self, event):
        if event['order_id'] not in self.orders:
            raise ValueError('event wasnt added')
        
        order = self.orders[event['order_id']]
        if order['side'] == 'bid':
            self.bids[order['price']] = self.bids.get(order['price'], 0) - order['size'] + event['size']
        else:
            self.asks[order['price']] = self.asks.get(order['price'], 0) - order['size'] + event['size']

        self.orders[event['order_id']]['size'] = event['size']

    def _process_cancel_event(self, event):
        if event['order_id'] not in self.orders:
            raise ValueError('event wasnt added')
        order = self.orders.pop(event['order_id'])
        
        if order['side'] == 'bid':
            self.bids[order['price']] -= order['size']
            if math.isclose(self.bids[order['price']], 0, abs_tol=1e-8):
                del self.bids[order['price']]
        else:
            self.asks[order['price']] -= order['size']
            if math.isclose(self.asks[order['price']], 0, abs_tol=1e-8):
                del self.asks[order['price']]

    def _process_trade_event(self, event):
        if event['order_id'] not in self.orders:
            raise ValueError('event wasnt added')
        order = self.orders[event['order_id']]
        
        if order['side'] == 'bid':
            self.bids[order['price']] -= event['size']
            if math.isclose(self.bids[order['price']], 0, abs_tol=1e-8):
                del self.bids[order['price']]
        else:
            self.asks[order['price']] -= event['size']
            if math.isclose(self.asks[order['price']], 0, abs_tol=1e-8):
                del self.asks[order['price']]
        
        self.orders[event['order_id']]['size'] = order['size'] - event['size']
        if math.isclose(self.orders[event['order_id']]['size'], 0, abs_tol=1e-8):
            del self.orders[event['order_id']]
    
    def snapshot(self, depth):
        return {
            'bids': sorted(self.bids.items(), reverse=True)[:depth],
            'asks': sorted(self.asks.items())[:depth]
        }

# -----------------------------------------------------------------------------
# SECTION 2 — Data loading
# -----------------------------------------------------------------------------

def load_real_data(filepath: str) -> list[dict]:
    events = []
    with open(filepath, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            event = {
                'timestamp':  float(row['timestamp']),
                'order_id':   row['order_id'],
                'event_type': row['event_type'],
            }
            if row.get('side'):  event['side']  = row['side']
            if row.get('price'): event['price'] = float(row['price'])
            if row.get('size'):  event['size']  = float(row['size'])
            events.append(event)
    return events

def simulate_btc_perp_events(n_orders: int = 800, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    np.random.seed(seed)

    mid = 65_000.0          # starting BTC price
    tick = 0.50             # $0.50 tick
    events = []
    ts = 0
    live_orders = {}        # order_id -> {'side', 'price', 'size'}
    order_counter = 0

    def next_id():
        nonlocal order_counter
        order_counter += 1
        return f"O{order_counter:05d}"

    for _ in range(n_orders):
        ts += rng.randint(1, 10)

        # slowly drift mid-price
        mid += np.random.normal(0, 2)

        # cancel stale orders that would cross the book after mid drift
        stale = [oid for oid, o in list(live_orders.items())
                 if (o['side'] == 'bid' and o['price'] >= mid) or
                    (o['side'] == 'ask' and o['price'] <= mid)]
        for oid in stale:
            del live_orders[oid]
            events.append({'timestamp': ts, 'order_id': oid, 'event_type': 'cancel'})

        if not live_orders:
            choice = 'new'
        else:
            choice = rng.choices(
                ['new', 'cancel', 'modify', 'trade'],
                weights=[0.55, 0.20, 0.10, 0.15]
            )[0]

        if choice == 'new':
            side  = rng.choice(['bid', 'ask'])
            offset = rng.randint(0, 5) * tick
            price = round(mid - offset, 2) if side == 'bid' else round(mid + offset, 2)
            size  = rng.randint(1, 20) * 0.01
            oid   = next_id()
            live_orders[oid] = {'side': side, 'price': price, 'size': size}
            events.append({
                'timestamp': ts, 'order_id': oid, 'event_type': 'new',
                'side': side, 'price': price, 'size': size
            })

        elif choice == 'cancel':
            oid = rng.choice(list(live_orders.keys()))
            del live_orders[oid]
            events.append({'timestamp': ts, 'order_id': oid, 'event_type': 'cancel'})

        elif choice == 'modify':
            oid   = rng.choice(list(live_orders.keys()))
            new_size = max(0.01, live_orders[oid]['size'] + rng.uniform(-0.05, 0.05))
            new_size = round(new_size, 2)
            live_orders[oid]['size'] = new_size
            events.append({'timestamp': ts, 'order_id': oid, 'event_type': 'modify', 'size': new_size})

        else:  # trade
            oid = rng.choice(list(live_orders.keys()))
            order = live_orders[oid]
            trade_size = min(order['size'], round(rng.uniform(0.01, order['size']), 2))
            events.append({
                'timestamp': ts, 'order_id': oid, 'event_type': 'trade',
                'price': order['price'],
                'size': trade_size
            })
            # FIX: Round the remaining size to avoid float precision issues causing de-syncs
            order['size'] = round(order['size'] - trade_size, 4)
            if order['size'] <= 0:
                del live_orders[oid]

    return events

# -----------------------------------------------------------------------------
# SECTION 3 — Replay engine
# -----------------------------------------------------------------------------

def replay_events(events: list[dict]) -> tuple[list, list, list, list]:
    book = OrderBook()
    timestamps     = []
    mid_prices     = []
    quoted_spreads = []
    trade_prices   = []

    for event in events:
        book._process_events(event)

        snap = book.snapshot(depth=1)
        bids = snap['bids']
        asks = snap['asks']

        if bids and asks:
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            mid    = (best_bid + best_ask) / 2.0
            spread = best_ask - best_bid
        else:
            mid    = float('nan')
            spread = float('nan')

        timestamps.append(event['timestamp'])
        mid_prices.append(mid)
        quoted_spreads.append(spread)

        if event['event_type'] == EventType.TRADE.value:
            trade_price = event.get('price', mid)
            trade_prices.append((event['timestamp'], trade_price))

    return timestamps, mid_prices, quoted_spreads, trade_prices

# -----------------------------------------------------------------------------
# SECTION 4 — Roll Estimator
# -----------------------------------------------------------------------------

def roll_estimator(trade_prices: list[float]) -> float:
    prices = np.array(trade_prices, dtype=float)
    if len(prices) < 3:
        return float('nan')

    delta_p = np.diff(prices)                        # ΔP_t series
    cov = np.cov(delta_p[:-1], delta_p[1:])[0, 1]   # Cov(ΔP_t, ΔP_{t-1})

    if cov >= 0:
        return float('nan')

    return 2.0 * np.sqrt(-cov)

# -----------------------------------------------------------------------------
# SECTION 5 — Main analysis + plots
# -----------------------------------------------------------------------------

def run_q2_analysis(events: list[dict]) -> None:
    timestamps, mid_prices, quoted_spreads, trade_prices_ts = replay_events(events)

    trade_prices = [p for _, p in trade_prices_ts]
    trade_ts     = [t for t, _ in trade_prices_ts]

    roll_spread    = roll_estimator(trade_prices)
    avg_quoted     = float(np.nanmean(quoted_spreads))
    median_quoted  = float(np.nanmedian(quoted_spreads))

    window = 50
    rolling_roll = []
    rolling_ts   = []
    for i in range(window, len(trade_prices) + 1):
        rs = roll_estimator(trade_prices[i - window:i])
        rolling_roll.append(rs)
        rolling_ts.append(trade_ts[i - 1])

    fig = plt.figure(figsize=(14, 10))
    fig.patch.set_facecolor('#0f1117')
    gs = gridspec.GridSpec(3, 1, hspace=0.45)

    GOLD   = '#f0c040'
    TEAL   = '#3dd6c8'
    RED    = '#e05c5c'
    GREY   = '#8888aa'
    BG     = '#0f1117'
    PANEL  = '#1a1d27'

    def style_ax(ax):
        ax.set_facecolor(PANEL)
        ax.tick_params(colors=GREY, labelsize=8)
        ax.xaxis.label.set_color(GREY)
        ax.yaxis.label.set_color(GREY)
        for spine in ax.spines.values():
            spine.set_edgecolor('#2a2d3a')

    # — Plot 1: mid-price ---
    ax1 = fig.add_subplot(gs[0])
    style_ax(ax1)
    ax1.plot(timestamps, mid_prices, color=TEAL, linewidth=0.8, label='Mid-price')
    ax1.set_title('Mid-Price over Time  (BTC-PERP)', color='white', fontsize=10, pad=6)
    ax1.set_ylabel('Price ($)', fontsize=8)
    ax1.legend(fontsize=7, facecolor=PANEL, edgecolor='none', labelcolor='white')

    # — Plot 2: quoted spread over time ---
    ax2 = fig.add_subplot(gs[1])
    style_ax(ax2)
    ax2.plot(timestamps, quoted_spreads, color=GOLD, linewidth=0.7, alpha=0.85, label='Quoted spread')
    ax2.axhline(avg_quoted,   color=RED,  linewidth=1.2, linestyle='--', label=f'Mean quoted  = {avg_quoted:.4f}')
    if not np.isnan(roll_spread):
        ax2.axhline(roll_spread, color='white', linewidth=1.2, linestyle=':',  label=f'Roll estimate = {roll_spread:.4f}')
    ax2.set_title('Quoted Spread vs Roll Effective Spread', color='white', fontsize=10, pad=6)
    ax2.set_ylabel('Spread ($)', fontsize=8)
    ax2.legend(fontsize=7, facecolor=PANEL, edgecolor='none', labelcolor='white')

    # — Plot 3: rolling Roll estimator ---
    ax3 = fig.add_subplot(gs[2])
    style_ax(ax3)
    valid = [(t, r) for t, r in zip(rolling_ts, rolling_roll) if not np.isnan(r)]
    if valid:
        vt, vr = zip(*valid)
        ax3.plot(vt, vr, color='#a78bfa', linewidth=0.9, label=f'Rolling Roll (w={window})')
    ax3.axhline(avg_quoted, color=GOLD, linewidth=1.0, linestyle='--', label=f'Mean quoted = {avg_quoted:.4f}')
    ax3.set_title(f'Rolling Roll Estimator  (window = {window} trades)', color='white', fontsize=10, pad=6)
    ax3.set_ylabel('Effective Spread ($)', fontsize=8)
    ax3.set_xlabel('Timestamp', fontsize=8)
    ax3.legend(fontsize=7, facecolor=PANEL, edgecolor='none', labelcolor='white')

    plt.savefig('q2_roll_analysis.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.show()  # Display inline in Colab
    plt.close()

    # --- print summary ---
    print("=" * 60)
    print("Q2 — Roll Estimator Results")
    print("=" * 60)
    print(f"  Number of trade events          : {len(trade_prices)}")
    print(f"  Roll effective spread estimate  : {roll_spread:.4f}" if not np.isnan(roll_spread) else "  Roll effective spread estimate  : NaN (cov >= 0)")
    print(f"  Mean quoted spread              : {avg_quoted:.4f}")
    print(f"  Median quoted spread            : {median_quoted:.4f}")
    if not np.isnan(roll_spread):
        ratio = roll_spread / avg_quoted
        print(f"  Roll / Quoted ratio             : {ratio:.3f}")
    print()
    print("COMMENTARY")
    print("-" * 60)
    if np.isnan(roll_spread):
        print(
            "  Roll estimator returned NaN — the serial covariance of price\n"
            "  changes is non-negative. This typically means the market is\n"
            "  trending strongly enough that the bid-ask bounce signal is\n"
            "  swamped by directional moves. This is common in crypto.\n"
            "  Consider computing Roll over shorter, calmer sub-windows."
        )
    elif roll_spread > avg_quoted:
        print(
            f"  Roll ({roll_spread:.4f}) > quoted spread ({avg_quoted:.4f}).\n"
            "  This suggests traders face hidden execution costs beyond the\n"
            "  posted spread — consistent with adverse selection: informed\n"
            "  order flow causes prices to move against the market maker\n"
            "  AFTER a trade, inflating the effective cost vs the quoted price.\n"
            "  In crypto, this is amplified by thin books and fast price moves."
        )
    else:
        print(
            f"  Roll ({roll_spread:.4f}) < quoted spread ({avg_quoted:.4f}).\n"
            "  The effective spread is narrower than the quoted spread.\n"
            "  Possible explanations:\n"
            "    1. Non-stationarity: the Roll model assumes a stable mid-price;\n"
            "       BTC's high volatility violates this and can compress the\n"
            "       estimated covariance.\n"
            "    2. Price improvement: trades may execute inside the spread\n"
            "       (e.g. hidden orders), making effective costs genuinely lower.\n"
            "    3. Sample size: with few trades the covariance estimate is noisy."
        )
    print("=" * 60)

# -----------------------------------------------------------------------------
# SECTION 6 — Entry point
# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # --- original smoke test ---
    events_smoke = [
        {'timestamp': 1, 'order_id': 'A1', 'event_type': 'new',    'side': 'bid', 'price': 213.50, 'size': 100},
        {'timestamp': 2, 'order_id': 'A2', 'event_type': 'new',    'side': 'bid', 'price': 213.45, 'size': 200},
        {'timestamp': 3, 'order_id': 'B1', 'event_type': 'new',    'side': 'ask', 'price': 213.55, 'size': 150},
        {'timestamp': 4, 'order_id': 'A1', 'event_type': 'cancel'},
        {'timestamp': 5, 'order_id': 'A2', 'event_type': 'modify',  'size': 50},
    ]
    book = OrderBook()
    for event in events_smoke:
        book._process_events(event)
    print("snapshot test:", book.snapshot(depth=5))
    print()

    # --- Q2 analysis ---
    print("Running Q2 analysis on simulated BTC-PERP data...")
    events_full = simulate_btc_perp_events(n_orders=1200)
    run_q2_analysis(events_full)
