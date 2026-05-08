from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

load_dotenv()

# ── State 定义 ────────────────────────────────────────
# 这次不用 MessagesState，自己定义，因为需要额外字段
class ContentState(TypedDict):
    messages:       Annotated[list, add_messages]
    draft_content:  str    # 当前生成的草稿
    revision_count: int    # 修改次数
    approved:       bool   # 是否已通过审核


# ── 工具定义 ──────────────────────────────────────────

BANNED_WORDS = ["免费", "100%", "必得", "保底", "内部", "绝密"]

@tool
def check_content_policy(content: str) -> str:
    """
    对生成的游戏公告内容进行合规检查。
    检测违禁词、长度限制、必要信息是否完整。
    返回检查结果，包含是否通过和具体问题。
    """
    issues = []

    # 检查违禁词
    found = [w for w in BANNED_WORDS if w in content]
    if found:
        issues.append(f"包含违禁词：{', '.join(found)}")

    # 检查长度
    if len(content) < 50:
        issues.append("内容过短，少于50字")
    if len(content) > 800:
        issues.append("内容过长，超过800字")

    # 检查是否有时间信息
    time_keywords = ["时间", "日期", "月", "日", "起", "至", "开始", "结束"]
    if not any(k in content for k in time_keywords):
        issues.append("缺少活动时间信息")

    if issues:
        return f"检查未通过，发现以下问题：\n" + "\n".join(f"- {i}" for i in issues)
    return "检查通过 ✓ 内容符合发布规范"


# ── 节点定义 ──────────────────────────────────────────

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
llm_with_tools = llm.bind_tools([check_content_policy])

SYSTEM_PROMPT = SystemMessage(content=(
    "你是游戏公司的内容运营，负责撰写游戏公告和活动文案。\n"
    "要求：\n"
    "- 语气活泼、吸引玩家，符合游戏风格\n"
    "- 必须包含活动时间、奖励内容、参与方式三要素\n"
    "- 生成内容后，必须调用 check_content_policy 工具进行合规检查\n"
    "- 若检查不通过，根据问题自动修正后再次检查\n"
    "- 检查通过后，将最终内容放在回复的最后，用 [最终公告] 标签包裹"
))


def generate_node(state: ContentState):
    """LLM 生成或修改内容，并自动做合规检查"""
    messages = [SYSTEM_PROMPT] + state["messages"]

    # 如果有修改意见，加进去
    if state.get("draft_content") and not state.get("approved"):
        pass  # 修改意见已经在 messages 里了

    # ReAct 循环：LLM 可能多次调用工具直到检查通过
    from langgraph.prebuilt import ToolNode
    tool_node = ToolNode([check_content_policy])

    response = llm_with_tools.invoke(messages)
    new_messages = [response]

    # 如果 LLM 调用了工具，执行工具并让 LLM 继续
    while response.tool_calls:
        tool_result = tool_node.invoke({"messages": state["messages"] + new_messages})
        new_messages += tool_result["messages"]
        response = llm_with_tools.invoke([SYSTEM_PROMPT] + state["messages"] + new_messages)
        new_messages.append(response)

    # 提取 [最终公告] 标签内的内容
    content = response.content
    draft = ""
    if "[最终公告]" in content:
        start = content.find("[最终公告]") + len("[最终公告]")
        end   = content.find("[/最终公告]") if "[/最终公告]" in content else len(content)
        draft = content[start:end].strip()
    else:
        draft = content  # 没有标签就用全文

    return {
        "messages":       new_messages,
        "draft_content":  draft,
        "revision_count": state.get("revision_count", 0),
    }


def human_review_node(state: ContentState):
    """
    核心节点：图在这里暂停，等待人工输入。
    输入"通过"则审核通过，输入其他内容则作为修改意见。
    """
    print("\n" + "="*50)
    print("📋 待审核内容：")
    print("-"*50)
    print(state["draft_content"])
    print("-"*50)
    print(f"（第 {state.get('revision_count', 0) + 1} 稿）")

    # interrupt 让图暂停，等待外部调用 Command(resume=...) 传入反馈
    feedback = interrupt({
        "draft":   state["draft_content"],
        "message": "请审核以上内容。输入「通过」发布，或输入具体修改意见："
    })

    if feedback.strip() == "通过":
        return {
            "approved":       True,
            "revision_count": state.get("revision_count", 0) + 1,
        }
    else:
        return {
            "approved":       False,
            "revision_count": state.get("revision_count", 0) + 1,
            "messages":       [HumanMessage(content=f"修改意见：{feedback}，请根据意见重新生成公告。")],
        }


def route_after_review(state: ContentState):
    """审核后的路由：通过则结束，否则回去重新生成"""
    if state.get("approved"):
        return END
    return "generate"


# ── 构建图 ────────────────────────────────────────────
graph = StateGraph(ContentState)
graph.add_node("generate",     generate_node)
graph.add_node("human_review", human_review_node)
graph.set_entry_point("generate")
graph.add_edge("generate", "human_review")
graph.add_conditional_edges("human_review", route_after_review)

# 关键：必须传入 checkpointer，interrupt 才能工作
memory   = MemorySaver()
agent    = graph.compile(checkpointer=memory)

# ── 运行入口 ──────────────────────────────────────────
def run():
    # thread_id 用于区分不同对话，同一个 thread 可以 resume
    config = {"configurable": {"thread_id": "content-001"}}

    task = "写一篇春节活动公告，活动时间2月1日至2月15日，登录送限定皮肤，累计充值满648送专属称号"

    print(f"\n任务：{task}\n")

    # 第一次调用，图会跑到 interrupt 处暂停
    result = agent.invoke(
        {
            "messages":       [HumanMessage(content=task)],
            "draft_content":  "",
            "revision_count": 0,
            "approved":       False,
        },
        config=config,
    )

    # 循环处理审核
    while True:
        # 检查图是否已结束
        state = agent.get_state(config)
        if not state.next:  # next 为空说明图已跑完
            print("\n✅ 公告已通过审核，流程结束。")
            print("\n最终发布内容：")
            print(agent.get_state(config).values["draft_content"])
            break

        # 图还在等待，读取人工输入
        feedback = input("\n请输入审核意见（输入「通过」发布）：").strip()

        # 用 Command(resume=...) 把反馈传回图，继续执行
        agent.invoke(Command(resume=feedback), config=config)


if __name__ == "__main__":
    run()

def generate_content(task: str) -> str:
    """
    Supervisor 专用：只生成内容，不做人工审核。
    直接返回生成的草稿字符串。
    """
    from langchain_core.messages import HumanMessage as HM
    state = {
        "messages":       [HM(content=task)],
        "draft_content":  "",
        "revision_count": 0,
        "approved":       False,
    }
    result = generate_node(state)
    return result.get("draft_content") or result["messages"][-1].content