import sqlite3
import random
from datetime import datetime, timedelta

# ── 基础配置 ──────────────────────────────────────────
DB_PATH = "data/game_data.db"
NUM_PLAYERS = 500
START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime(2024, 3, 31)

random.seed(42)  # 固定种子，每次生成结果一致

# ── 枚举数据 ──────────────────────────────────────────
CHANNELS      = ["广告投放", "应用商店", "好友邀请", "官网", "B站"]
DEVICES       = ["Android", "iOS", "PC"]
COUNTRIES     = ["CN", "CN", "CN", "US", "JP", "TW"]  # CN 权重更高
EVENT_TYPES   = ["login", "login", "login", "battle", "battle", "quest", "shop_visit", "logout"]
ITEMS         = [
    ("月卡",    "subscription", 30),
    ("648礼包", "gift_pack",   648),
    ("酋长礼包","gift_pack",   128),
    ("钻石×100","currency",    6),
    ("钻石×500","currency",    30),
    ("限定皮肤","skin",        188),
    ("体力药水", "consumable",  6),
]
PAYMENT_METHODS = ["支付宝", "微信支付", "苹果支付", "GooglePay"]

def rand_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))

def rand_date_str(start, end):
    return rand_date(start, end).strftime("%Y-%m-%d")

# ── 建库建表 ──────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS player_events;
DROP TABLE IF EXISTS player_purchases;

CREATE TABLE players (
    player_id       INTEGER PRIMARY KEY,
    register_date   TEXT NOT NULL,
    channel         TEXT,
    device_type     TEXT,
    player_level    INTEGER DEFAULT 1,
    vip_level       INTEGER DEFAULT 0,
    total_paid      REAL    DEFAULT 0.0,
    country         TEXT,
    is_active       INTEGER DEFAULT 1
);

CREATE TABLE player_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL,
    event_date      TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    session_minutes INTEGER,
    level_reached   INTEGER,
    stage_id        INTEGER,
    is_new_day      INTEGER DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE TABLE player_purchases (
    purchase_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL,
    purchase_date   TEXT NOT NULL,
    item_name       TEXT,
    item_type       TEXT,
    amount_rmb      REAL,
    payment_method  TEXT,
    is_first_pay    INTEGER DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);
""")

# ── 生成 players ──────────────────────────────────────
players = []
for pid in range(1001, 1001 + NUM_PLAYERS):
    reg_date = rand_date_str(START_DATE, END_DATE)

    # 付费玩家约占 30%
    is_payer   = random.random() < 0.3
    total_paid = round(random.uniform(6, 2000), 2) if is_payer else 0.0
    vip_level  = min(int(total_paid / 200), 8) if is_payer else 0

    players.append((
        pid,
        reg_date,
        random.choice(CHANNELS),
        random.choice(DEVICES),
        random.randint(1, 80),   # player_level
        vip_level,
        total_paid,
        random.choice(COUNTRIES),
        1 if random.random() > 0.15 else 0,   # 85% 活跃
    ))

cur.executemany("""
    INSERT INTO players VALUES (?,?,?,?,?,?,?,?,?)
""", players)

# ── 生成 player_events（约 3500 条）────────────────────
events = []
for pid, reg_date, *_ in players:
    reg_dt = datetime.strptime(reg_date, "%Y-%m-%d")

    # 每个玩家生成 5~12 条行为记录
    n_events   = random.randint(5, 12)
    seen_dates = set()

    for _ in range(n_events):
        ev_date = rand_date_str(reg_dt, END_DATE)
        events.append((
            pid,
            ev_date,
            random.choice(EVENT_TYPES),
            random.randint(5, 120),         # session_minutes
            random.randint(1, 80),          # level_reached
            random.randint(1, 200),         # stage_id
            1 if ev_date not in seen_dates else 0,   # is_new_day
        ))
        seen_dates.add(ev_date)

cur.executemany("""
    INSERT INTO player_events
        (player_id, event_date, event_type,
         session_minutes, level_reached, stage_id, is_new_day)
    VALUES (?,?,?,?,?,?,?)
""", events)

# ── 生成 player_purchases（约 1500 条）─────────────────
purchases = []
payer_ids  = [p[0] for p in players if p[6] > 0]   # total_paid > 0

for pid in payer_ids:
    # 每个付费玩家生成 1~6 笔充值
    n_purchases = random.randint(1, 6)
    is_first    = True

    for _ in range(n_purchases):
        item_name, item_type, base_price = random.choice(ITEMS)
        purchase_date = rand_date_str(START_DATE, END_DATE)

        purchases.append((
            pid,
            purchase_date,
            item_name,
            item_type,
            float(base_price),
            random.choice(PAYMENT_METHODS),
            1 if is_first else 0,
        ))
        is_first = False

cur.executemany("""
    INSERT INTO player_purchases
        (player_id, purchase_date, item_name,
         item_type, amount_rmb, payment_method, is_first_pay)
    VALUES (?,?,?,?,?,?,?)
""", purchases)

conn.commit()

# ── 验证结果 ──────────────────────────────────────────
for table in ["players", "player_events", "player_purchases"]:
    count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table:25s}: {count} 条")

print("\n--- 付费数据样例 ---")
rows = cur.execute("""
    SELECT p.player_id, p.vip_level, p.total_paid,
           COUNT(pu.purchase_id) AS 购买次数
    FROM players p
    JOIN player_purchases pu ON p.player_id = pu.player_id
    GROUP BY p.player_id
    ORDER BY p.total_paid DESC
    LIMIT 5
""").fetchall()
for row in rows:
    print(row)

conn.close()
print(f"\n数据库已保存至 {DB_PATH}")