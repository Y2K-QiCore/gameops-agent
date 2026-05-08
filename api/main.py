import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage
from agents.supervisor.graph import supervisor_graph

app = FastAPI(
    title="GameOps-Agent API",
    description="面向游戏公司的多智能体运营助手",
    version="1.0.0",
)

# 允许 Gradio 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 请求 / 响应结构体 ─────────────────────────────────
class ChatRequest(BaseModel):
    message:   str
    thread_id: Optional[str] = "default-session"

class ChatResponse(BaseModel):
    reply:      str
    thread_id:  str
    agent_used: str   # 是哪个子 Agent 回答的


# ── 工具函数：从回复内容推断使用了哪个 Agent ──────────
def detect_agent(reply: str) -> str:
    if reply.startswith("📊"):
        return "数据分析 Agent"
    elif reply.startswith("🎮"):
        return "客服 Agent"
    elif reply.startswith("✍️"):
        return "内容生成 Agent"
    elif reply.startswith("🔍"):
        return "技术调研 Agent"
    return "Supervisor"


# ── 接口定义 ──────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "GameOps-Agent"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        config = {"configurable": {"thread_id": req.thread_id}}

        result = supervisor_graph.invoke(
            {
                "messages":   [HumanMessage(content=req.message)],
                "next_agent": "",
            },
            config=config,
        )

        # 取最后一条 AI 消息
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        if not ai_messages:
            raise HTTPException(status_code=500, detail="Agent 未返回任何内容")

        reply = ai_messages[-1].content

        return ChatResponse(
            reply=reply,
            thread_id=req.thread_id,
            agent_used=detect_agent(reply),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    """获取指定会话的对话历史"""
    config = {"configurable": {"thread_id": thread_id}}
    state  = supervisor_graph.get_state(config)

    if not state or not state.values:
        return {"thread_id": thread_id, "messages": []}

    messages = []
    for m in state.values.get("messages", []):
        if isinstance(m, HumanMessage):
            messages.append({"role": "user",      "content": m.content})
        elif isinstance(m, AIMessage):
            messages.append({"role": "assistant", "content": m.content})

    return {"thread_id": thread_id, "messages": messages}