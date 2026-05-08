from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel
from dotenv import load_dotenv
import sys
from pathlib import Path
from agents.tech_researcher.agent import agent as tech_researcher_agent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from agents.data_analyst.agent     import agent as data_analyst_agent
from agents.customer_service.agent import agent as customer_service_agent
from agents.content_generator.agent import generate_content

# ── Supervisor 状态 ───────────────────────────────────
class SupervisorState(TypedDict):
    messages:   Annotated[list, add_messages]
    next_agent: str

# ── 路由决策结构体 ─────────────────────────────────────
class RouteDecision(BaseModel):
    next: Literal["data_analyst", "customer_service", "content_generator", "tech_researcher", "FINISH"]
    reason: str

# ── Supervisor 节点 ───────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

SUPERVISOR_PROMPT = """你是游戏公司 AI 运营平台的任务调度器。
根据对话历史决定下一步动作：

路由规则：
- data_analyst     ：数据查询、玩家留存、付费分析、渠道效果、报表
- customer_service ：玩家投诉、充值问题、账号问题、礼包未到账、封号申诉
- content_generator：写公告、活动文案、版本说明、运营推文
- tech_researcher  ：技术调研、竞品分析、行业动态、新技术方案调研
- FINISH           ：最后一条消息已经是 Agent 的完整回复，任务结束

重要：如果对话中最后一条消息是 AI 给出的回复内容，直接路由到 FINISH，不要重复处理。
只做调度决策，不要自己回答问题。"""

def supervisor_node(state: SupervisorState):
    decision = llm.with_structured_output(RouteDecision).invoke(
        [SystemMessage(content=SUPERVISOR_PROMPT)] + state["messages"]
    )
    print(f"\n[Supervisor] → {decision.next}（{decision.reason}）")
    return {"next_agent": decision.next}

def route_from_supervisor(state: SupervisorState):
    n = state["next_agent"]
    if n == "FINISH":
        return END
    return n

# ── 子 Agent 节点 ─────────────────────────────────────
def _get_last_user_message(state: SupervisorState) -> str:
    """从消息历史里取最后一条用户消息"""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            return m.content
    return ""

def data_analyst_node(state: SupervisorState):
    user_msg = _get_last_user_message(state)
    print(f"[数据分析 Agent] 处理中...")

    result = data_analyst_agent.invoke({
        "messages": [HumanMessage(content=user_msg)]
    })
    answer = result["messages"][-1].content
    return {
        "messages":   [AIMessage(content=f"📊 [数据分析]\n{answer}")],
        "next_agent": "",
    }

def customer_service_node(state: SupervisorState):
    user_msg = _get_last_user_message(state)
    print(f"[客服 Agent] 处理中...")

    result = customer_service_agent.invoke({
        "messages": [HumanMessage(content=user_msg)]
    })
    answer = result["messages"][-1].content
    return {
        "messages":   [AIMessage(content=f"🎮 [客服回复]\n{answer}")],
        "next_agent": "",
    }

def content_generator_node(state: SupervisorState):
    user_msg = _get_last_user_message(state)
    print(f"[内容生成 Agent] 处理中...")

    draft = generate_content(user_msg)
    return {
        "messages":   [AIMessage(content=f"✍️ [内容生成]\n{draft}")],
        "next_agent": "",
    }

def tech_researcher_node(state: SupervisorState):
    user_msg = _get_last_user_message(state)
    print(f"[技术调研 Agent] 处理中...")

    result = tech_researcher_agent.invoke({
        "messages": [{"role": "user", "content": user_msg}]
    })
    answer = result["messages"][-1].content
    return {
        "messages":   [AIMessage(content=f"🔍 [技术调研]\n{answer}")],
        "next_agent": "",
    }

# ── 构建主图 ──────────────────────────────────────────
graph = StateGraph(SupervisorState)

graph.add_node("supervisor",        supervisor_node)
graph.add_node("data_analyst",      data_analyst_node)
graph.add_node("customer_service",  customer_service_node)
graph.add_node("content_generator", content_generator_node)
graph.add_node("tech_researcher", tech_researcher_node)

graph.set_entry_point("supervisor")

graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "data_analyst":      "data_analyst",
        "customer_service":  "customer_service",
        "content_generator": "content_generator",
        "tech_researcher": "tech_researcher",
        END:                 END,
    }
)

# 每个子 Agent 完成后回到 Supervisor 决定是否结束
graph.add_edge("data_analyst",      "supervisor")
graph.add_edge("customer_service",  "supervisor")
graph.add_edge("content_generator", "supervisor")
graph.add_edge("tech_researcher", "supervisor")

memory         = MemorySaver()
supervisor_graph = graph.compile(checkpointer=memory)