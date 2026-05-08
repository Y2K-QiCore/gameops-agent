from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode
from memory.player_memory import player_memory

load_dotenv()

VECTORSTORE_DIR = Path(__file__).parent.parent.parent / "data" / "vectorstore"

# ── 加载向量库 ────────────────────────────────────────
embeddings  = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    persist_directory=str(VECTORSTORE_DIR),
    embedding_function=embeddings,
    collection_name="game_faq",
)

# ── 工具定义 ──────────────────────────────────────────
# 在文件顶部 import 区域加这一行

@tool
def get_player_history(player_id: str) -> str:
    """
    查询玩家的历史联系客服记录。
    当玩家提供了 player_id 时调用，用于了解该玩家是否有重复投诉。
    如果玩家是多次投诉同一问题，需要在回复中体现更高的重视程度。
    """
    return player_memory.summary(player_id)


@tool
def save_contact_record(player_id: str, issue_summary: str) -> str:
    """
    将本次玩家咨询记录保存到长期记忆，供下次查询使用。
    每次成功处理玩家问题后调用此工具。
    player_id: 玩家ID
    issue_summary: 本次问题的简短描述（20字以内）
    """
    player_memory.record_contact(player_id, issue_summary)
    return f"已记录玩家 {player_id} 的咨询记录。"

@tool
def search_knowledge_base(query: str) -> str:
    """
    从游戏客服知识库中检索与玩家问题相关的解决方案。
    适用于充值问题、账号问题、游戏内bug、活动福利等各类玩家咨询。
    返回最相关的知识库内容，相似度低于阈值时返回未找到。
    """
    results = vectorstore.similarity_search_with_relevance_scores(query, k=3)

    if not results or results[0][1] < 0.3:
        return "知识库中未找到相关解决方案，建议转人工客服处理。"

    output = "以下是知识库中的相关内容：\n\n"
    for doc, score in results:
        category = doc.metadata.get("category", "")
        question = doc.metadata.get("question", "")
        output += f"【{category} - {question}】（相关度{score:.2f}）\n"
        output += doc.page_content + "\n\n"
    return output


@tool
def create_ticket(
    player_issue: str,
    issue_type: str,
    priority: str,
) -> str:
    """
    当问题无法通过知识库解决时，创建人工客服工单。
    player_issue: 玩家问题的简要描述
    issue_type:   问题分类，可选 充值问题/账号问题/游戏bug/其他
    priority:     优先级，可选 高/中/低
                  - 高：账号被盗、重复扣款
                  - 中：充值未到账、礼包未收到
                  - 低：游戏建议、活动咨询
    """
    import datetime, random
    ticket_id = f"TK{datetime.date.today().strftime('%Y%m%d')}{random.randint(1000,9999)}"

    return (
        f"工单已创建 ✓\n"
        f"工单号：{ticket_id}\n"
        f"问题描述：{player_issue}\n"
        f"问题类型：{issue_type}\n"
        f"优先级：{priority}\n"
        f"预计处理时间：{'2小时内' if priority == '高' else '24小时内'}\n"
        f"请玩家保留工单号，客服将通过游戏内邮件回复。"
    )


# ── 构建 StateGraph ───────────────────────────────────
tools = [search_knowledge_base, create_ticket, get_player_history, save_contact_record]

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_with_tools = llm.bind_tools(tools)

SYSTEM_PROMPT = SystemMessage(content=(
     "你是一名专业的游戏客服，负责解答玩家的问题。\n"
    "处理流程：\n"
    "1. 如果玩家提供了 player_id，先调用 get_player_history 查询历史记录\n"
    "2. 调用 search_knowledge_base 工具检索解决方案\n"
    "3. 如果知识库有答案，用友好的语气整理后回复玩家\n"
    "4. 如果是账号安全/重复扣款等紧急情况，调用 create_ticket 创建工单\n"
    "5. 处理完毕后，调用 save_contact_record 保存本次记录\n"
    "注意：若玩家是第2次以上反馈同一问题，要在回复中表达歉意并提升优先级。"
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
graph.add_node("llm", call_llm)
graph.add_node("tools", tool_node)
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", should_continue)
graph.add_edge("tools", "llm")

agent = graph.compile()


# ── 测试入口 ──────────────────────────────────────────
def ask(question: str):
    print(f"\n{'='*50}")
    print(f"玩家：{question}")
    print('='*50)
    response = agent.invoke({
        "messages": [{"role": "user", "content": question}]
    })
    print(f"客服：{response['messages'][-1].content}")


if __name__ == "__main__":
    # 知识库能答的问题
    ask("我充值了648元但是钻石没有到账，怎么办？")
    ask("我的月卡买了但是没有生效")

    # 知识库答不了的，应该创建工单
    ask("我账号里的限定皮肤不见了，昨天还有的")

    # 紧急情况，应该高优先级工单
    ask("我的账号被别人登录了，道具全被转走了！")