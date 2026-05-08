from dotenv import load_dotenv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
load_dotenv()

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode

# ── 工具定义 ──────────────────────────────────────────

tavily = TavilySearch(max_results=5)

@tool
def search_web(query: str) -> str:
    """
    搜索互联网上的最新技术资讯、行业动态、竞品信息。
    适合查询：游戏AI技术进展、竞品游戏新功能、行业报告、技术方案对比。
    query 建议用英文或中英混合以获得更好结果。
    """
    results = tavily.invoke(query)

    if not results:
        return "未找到相关结果"

    output = ""
    for i, r in enumerate(results, 1):
        if isinstance(r, dict):
            output += f"[{i}] 来源：{r.get('url', '')}\n"
            output += f"    摘要：{r.get('content', '')[:200]}...\n\n"
        else:
            # 直接是字符串的情况
            output += f"[{i}] {str(r)[:300]}\n\n"
    return output

@tool
def evaluate_search_quality(search_results: str, original_query: str) -> str:
    """
    评估搜索结果是否足够回答原始查询。
    如果结果不够，返回建议的改进查询词；如果足够，返回"结果充足"。
    search_results: 搜索结果文本
    original_query: 原始查询问题
    """
    # 规则判断：结果是否有实质内容
    if "未找到相关结果" in search_results:
        return f"结果不足，建议改用英文查询：请将'{original_query}'翻译成英文后重新搜索"

    result_count = search_results.count("[")
    if result_count < 2:
        return f"结果数量不足（仅{result_count}条），建议换一个角度查询：尝试搜索更具体的关键词"

    # 检查内容相关性（简单关键词匹配）
    query_words = set(original_query.replace("，", " ").replace("、", " ").split())
    matched = sum(1 for w in query_words if len(w) > 1 and w in search_results)
    if matched == 0:
        return f"结果与查询相关性低，建议重新组织查询词"

    return "结果充足，可以整理报告"


# ── 构建 Agent ────────────────────────────────────────
tools = [search_web, evaluate_search_quality]

llm             = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
llm_with_tools  = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(content=(
    "你是一名游戏行业技术调研专员，负责搜集最新的技术资讯和竞品动态。\n"
    "工作流程：\n"
    "1. 根据调研主题，设计合适的搜索关键词（中英文都可以）\n"
    "2. 调用 search_web 进行搜索\n"
    "3. 调用 evaluate_search_quality 评估结果质量\n"
    "4. 如果质量不足，根据建议改进关键词，再次搜索（最多搜索3次）\n"
    "5. 结果充足后，整理成结构化的调研报告，包含：核心发现、主要趋势、参考来源\n"
    "报告要简洁，每个要点不超过3句话。"
))


def call_llm(state: MessagesState):
    messages = [SYSTEM_PROMPT] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: MessagesState):
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


tool_node = ToolNode(tools)

graph = StateGraph(MessagesState)
graph.add_node("llm",   call_llm)
graph.add_node("tools", tool_node)
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", should_continue)
graph.add_edge("tools", "llm")

agent = graph.compile()


# ── 测试入口 ──────────────────────────────────────────
def ask(question: str):
    print(f"\n{'='*50}")
    print(f"调研主题：{question}")
    print('='*50)
    response = agent.invoke({
        "messages": [{"role": "user", "content": question}]
    })
    print(response["messages"][-1].content)


if __name__ == "__main__":
    ask("调研一下2024年游戏行业AI NPC的最新进展，有哪些代表性产品")
    ask("LangGraph 和 AutoGen 在多Agent编排上有什么区别，各自适合什么场景")