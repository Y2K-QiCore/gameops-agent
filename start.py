"""
GameOps-Agent 一键启动脚本
运行方式：python start.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ENV_PATH = ROOT / ".env"

# ── 需要检查的 Key ─────────────────────────────────────
REQUIRED_KEYS = {
    "OPENAI_API_KEY":        "OpenAI API Key（sk-...）",
    "LANGCHAIN_API_KEY":     "LangSmith API Key（ls__...）（直接回车跳过）",
    "TAVILY_API_KEY":        "Tavily API Key（tvly-...）（直接回车跳过）",
}

OPTIONAL_KEYS = {"LANGCHAIN_API_KEY", "TAVILY_API_KEY"}


def load_env() -> dict:
    """读取现有 .env 文件"""
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def save_env(env: dict):
    """把 key-value 写回 .env 文件"""
    lines = [
        "# GameOps-Agent 环境变量\n",
        "# 自动生成，可手动修改\n\n",
        "# OpenAI\n",
        f"OPENAI_API_KEY={env.get('OPENAI_API_KEY', '')}\n\n",
        "# LangSmith 可观测性（可选）\n",
        f"LANGCHAIN_API_KEY={env.get('LANGCHAIN_API_KEY', '')}\n",
        "LANGCHAIN_TRACING_V2=true\n",
        "LANGCHAIN_PROJECT=gameops-agent\n\n",
        "# Tavily 搜索（可选，技术调研Agent需要）\n",
        f"TAVILY_API_KEY={env.get('TAVILY_API_KEY', '')}\n",
    ]
    ENV_PATH.write_text("".join(lines), encoding="utf-8")


def check_and_fill_keys():
    """检查 .env，缺少的 key 提示用户输入"""
    print("=" * 55)
    print("  GameOps-Agent 启动检查")
    print("=" * 55)

    env = load_env()
    changed = False

    for key, description in REQUIRED_KEYS.items():
        existing = env.get(key, "").strip()

        if existing:
            masked = existing[:8] + "..." if len(existing) > 8 else "***"
            print(f"  ✅ {key} 已配置（{masked}）")
            continue

        # 必填项且为空
        is_optional = key in OPTIONAL_KEYS
        if not is_optional:
            print(f"\n  ❌ 缺少 {key}")
        else:
            print(f"\n  ⚠️  缺少 {key}（可选）")

        value = input(f"     请输入 {description}：").strip()

        if value:
            env[key] = value
            changed = True
        elif not is_optional:
            print(f"\n  ✋ {key} 是必填项，无法启动。")
            print("     请在 .env 文件中填写后重新运行。")
            sys.exit(1)

    if changed:
        save_env(env)
        print("\n  💾 已保存到 .env 文件\n")
    else:
        print()

    return env


def start_services():
    """同时启动 FastAPI 和 Gradio"""
    print("=" * 55)
    print("  正在启动服务...")
    print("=" * 55)

    python = sys.executable

    # 启动 FastAPI
    print("\n  🚀 启动 FastAPI 后端 → http://127.0.0.1:8000")
    api_proc = subprocess.Popen(
        [python, "-m", "uvicorn", "api.main:app",
         "--reload", "--port", "8000"],
        cwd=ROOT,
    )

    # 等 2 秒让 FastAPI 先起来
    import time
    time.sleep(2)

    # 启动 Gradio
    print("  🎮 启动 Gradio 前端   → http://127.0.0.1:7860")
    ui_proc = subprocess.Popen(
        [python, "ui/app.py"],
        cwd=ROOT,
    )

    print("\n  ✅ 两个服务已启动")
    print("  📊 FastAPI 文档：http://127.0.0.1:8000/docs")
    print("  🎮 Gradio 界面：http://127.0.0.1:7860")
    print("  🔍 LangSmith：  https://smith.langchain.com")
    print("\n  按 Ctrl+C 停止所有服务\n")

    try:
        # 等待两个进程，任意一个退出就退出
        api_proc.wait()
        ui_proc.wait()
    except KeyboardInterrupt:
        print("\n\n  正在关闭服务...")
        api_proc.terminate()
        ui_proc.terminate()
        print("  已停止，再见！")


if __name__ == "__main__":
    check_and_fill_keys()
    start_services()