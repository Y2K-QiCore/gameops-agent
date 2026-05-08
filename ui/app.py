import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uuid
import requests
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:8000"

# ── 预置示例问题，方便演示 ────────────────────────────
EXAMPLES = [
    "1月份各渠道的付费转化率是多少？",
    "VIP等级最高的5个玩家总充值是多少？",
    "我是玩家1001，充值了648元但钻石没到账",
    "我的账号被盗了，道具全没了！",
    "帮我写一篇五一劳动节活动公告，5月1日至5月7日，登录送限定皮肤",
    "调研一下2024年游戏行业AI NPC的最新进展",
]


def chat(user_message: str, history: list, thread_id: str):
    """发送消息到 FastAPI，返回回复和 Agent 标签"""
    if not user_message.strip():
        return history, "", thread_id, ""

    try:
        resp = requests.post(
            f"{API_URL}/chat",
            json={"message": user_message, "thread_id": thread_id},
            timeout=60,
        )
        resp.raise_for_status()
        data       = resp.json()
        reply      = data["reply"]
        agent_used = data["agent_used"]

    except requests.exceptions.ConnectionError:
        reply      = "❌ 无法连接到后端服务，请先启动 FastAPI（uvicorn api.main:app --reload）"
        agent_used = "错误"
    except Exception as e:
        reply      = f"❌ 请求失败：{str(e)}"
        agent_used = "错误"

    history.append({"role": "user",      "content": user_message})
    history.append({"role": "assistant", "content": reply})

    return history, "", thread_id, f"🤖 由 **{agent_used}** 处理"


def clear_chat():
    """清空对话，生成新的 thread_id"""
    return [], "", str(uuid.uuid4())[:8], ""


# ── Gradio 界面 ───────────────────────────────────────
with gr.Blocks(title="GameOps-Agent") as demo:

    # 顶部标题
    gr.Markdown("""
    # 🎮 GameOps-Agent
    ### 面向游戏公司的多智能体运营助手
    支持：数据分析 · 玩家客服 · 内容生成 · 技术调研
    """)

    with gr.Row():
        with gr.Column(scale=4):

            # 对话框
            chatbot = gr.Chatbot(
                label="对话",
                height=480,
            )

            # 输入行
            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="输入你的问题，例如：1月份付费转化率是多少？",
                    label="",
                    scale=5,
                    lines=1,
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)

            # Agent 标签显示
            agent_label = gr.Markdown("")

            # 示例问题
            gr.Examples(
                examples=EXAMPLES,
                inputs=msg_box,
                label="示例问题（点击填入）",
            )

        with gr.Column(scale=1):
            gr.Markdown("### 会话信息")
            thread_display = gr.Textbox(
                label="会话 ID",
                value=str(uuid.uuid4())[:8],
                interactive=False,
            )
            clear_btn = gr.Button("🗑️ 清空对话", variant="secondary")

            gr.Markdown("""
            ### 路由规则
            - 📊 数据查询 → 数据分析
            - 🎮 玩家问题 → 客服
            - ✍️ 写文案 → 内容生成
            - 🔍 技术调研 → 调研Agent
            """)

            gr.Markdown("""
            ### 监控
            [查看 LangSmith Trace](https://smith.langchain.com)
            """)

    # 状态变量（存 thread_id）
    thread_id_state = gr.State(str(uuid.uuid4())[:8])

    # 事件绑定
    send_btn.click(
        fn=chat,
        inputs=[msg_box, chatbot, thread_id_state],
        outputs=[chatbot, msg_box, thread_id_state, agent_label],
    )
    msg_box.submit(
        fn=chat,
        inputs=[msg_box, chatbot, thread_id_state],
        outputs=[chatbot, msg_box, thread_id_state, agent_label],
    )
    clear_btn.click(
        fn=clear_chat,
        outputs=[chatbot, msg_box, thread_id_state, agent_label],
    )
    # 同步会话ID显示
    thread_id_state.change(
        fn=lambda x: x,
        inputs=thread_id_state,
        outputs=thread_display,
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft(),
    )