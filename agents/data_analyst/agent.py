import sqlite3
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode

load_dotenv()

# ── 数据库路径 ────────────────────────────────────────
DB_PATH = Path(__file__).parent.parent.parent / "data" / "game_data.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

# ── 工具定义 ──────────────────────────────────────────

@tool
def query_game_data(sql: str) -> str:
    """
    对游戏玩家数据库执行 SQL 查询并返回结果。

    数据库共有三张表：

    1. players（500条）—— 玩家档案
       - player_id      INTEGER  玩家唯一ID（1001起）
       - register_date  TEXT     注册日期，格式 YYYY-MM-DD
       - channel        TEXT     注册渠道：广告投放/应用商店/好友邀请/官网/B站
       - device_type    TEXT     设备类型：Android/iOS/PC
       - player_level   INTEGER  当前等级 1-80
       - vip_level      INTEGER  VIP等级 0-8
       - total_paid     REAL     累计充值金额（元），0表示未付费
       - country        TEXT     国家代码：CN/US/JP/TW
       - is_active      INTEGER  是否活跃：1活跃 0流失

    2. player_events（约3800条）—— 行为日志
       - event_id       INTEGER  自增主键
       - player_id      INTEGER  关联 players.player_id
       - event_date     TEXT     事件日期，格式 YYYY-MM-DD
       - event_type     TEXT     事件类型：login/battle/quest/shop_visit/logout
       - session_minutes INTEGER 本次在线时长（分钟）
       - level_reached  INTEGER  本次达到的等级
       - stage_id       INTEGER  关卡ID
       - is_new_day     INTEGER  是否当天首次登录：1是 0否

    3. player_purchases（约1400条）—— 充值记录
       - purchase_id    INTEGER  自增主键
       - player_id      INTEGER  关联 players.player_id
       - purchase_date  TEXT     充值日期，格式 YYYY-MM-DD
       - item_name      TEXT     商品名：月卡/648礼包/酋长礼包/钻石×100等
       - item_type      TEXT     subscription/gift_pack/currency/skin/consumable
       - amount_rmb     REAL     充值金额（元）
       - payment_method TEXT     支付方式：支付宝/微信支付/苹果支付/GooglePay
       - is_first_pay   INTEGER  是否首次付费：1是 0否

    数据时间范围：2024-01-01 至 2024-03-31
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return "查询结果为空"

        header = " | ".join(cols)
        sep    = "-" * len(header)
        body   = "\n".join(" | ".join(str(v) for v in row) for row in rows)
        return f"{header}\n{sep}\n{body}\n\n共 {len(rows)} 条结果"

    except Exception as e:
        return f"SQL 执行错误：{e}"


@tool
def get_table_schema(table_name: str) -> str:
    """
    查询指定表的字段结构，当不确定字段名时调用。
    table_name 可选值：players / player_events / player_purchases
    """
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return f"表 {table_name} 不存在"

        result = f"表 {table_name} 的字段结构：\n"
        for row in rows:
            result += f"  {row[1]}  {row[2]}\n"
        return result

    except Exception as e:
        return f"错误：{e}"


# ── 构建 StateGraph ───────────────────────────────────
tools = [query_game_data, get_table_schema]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(content=(
    "你是一个游戏数据分析师，擅长通过 SQL 查询玩家数据并给出业务洞察。\n"
    "回答时先给出数据结果，再给出1-2句业务解读。\n"
    "如果需要查询多张表，可以多次调用工具。"
))

def call_llm(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: MessagesState):
    last = state["messages"][-1]
    # 如果 LLM 决定调用工具，走 tools 分支；否则结束
    if last.tool_calls:
        return "tools"
    return END

tool_node = ToolNode(tools)

graph = StateGraph(MessagesState)
graph.add_node("llm", call_llm)
graph.add_node("tools", tool_node)
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", should_continue)
graph.add_edge("tools", "llm")   # 工具执行完回到 LLM

agent = graph.compile()


# ── 测试入口 ──────────────────────────────────────────
def ask(question: str):
    print(f"\n{'='*50}")
    print(f"问题：{question}")
    print('='*50)

    response = agent.invoke({
        "messages": [{"role": "user", "content": question}]
    })
    print(response["messages"][-1].content)


if __name__ == "__main__":
    ask("一共有多少玩家？其中付费玩家占比多少？")
    ask("各注册渠道的玩家数量分别是多少？哪个渠道效果最好？")
    ask("1月份每周的充值总金额是多少？")
    ask("VIP等级最高的5个玩家，他们的总充值和购买次数分别是多少？")