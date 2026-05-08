# 🎮 GameOps-Agent

> 面向游戏公司的多智能体 AI 运营助手系统  
> A Multi-Agent AI Operations Platform for Game Companies

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.0%2B-green)](https://github.com/langchain-ai/langgraph)
[![LangChain](https://img.shields.io/badge/LangChain-Latest-orange)](https://github.com/langchain-ai/langchain)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gradio](https://img.shields.io/badge/Gradio-Latest-FF7C00)](https://gradio.app)

---

## 📖 项目简介

GameOps-Agent 是一个基于 **LangGraph + LangChain** 构建的 Multi-Agent 系统，模拟游戏公司内部的 AI 运营中台。系统通过 Supervisor 主控节点统一调度四个专业子 Agent，覆盖游戏运营的核心场景：数据分析、玩家客服、内容生成与技术调研。

### ✨ 核心特性

- 🧠 **Multi-Agent 编排** — 基于 LangGraph StateGraph，Supervisor 自动识别意图并路由到对应 Agent
- 🔍 **RAG 知识库检索** — ChromaDB 向量存储 + OpenAI Embeddings，客服 Agent 精准召回解决方案
- 🔄 **Human-in-the-loop** — 内容生成 Agent 支持人工审批与多轮迭代修改
- 💾 **长期记忆层** — 跨会话存储玩家档案，支持多次投诉识别与差异化处理
- 🌐 **工具链集成** — SQL 查询、网络搜索（Tavily）、代码执行、RAG 检索四类工具
- 📊 **可观测性** — LangSmith 全链路 Trace，监控 Token 消耗、延迟与 Agent 决策
- 🚀 **工程化部署** — FastAPI 后端接口 + Gradio 前端界面，一键启动

---

## 🏗️ 系统架构

```
用户请求
    │
    ▼
┌─────────────────────────────────┐
│         Supervisor Agent         │
│   意图识别 · 任务分解 · 结果聚合   │
└──────┬──────┬──────┬────────────┘
       │      │      │      │
       ▼      ▼      ▼      ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
  │ Agent  │ │ Agent  │ │ Agent  │ │ Agent  │
  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
  SQL查询    RAG知识库   内容审核   Tavily搜索
  SQLite     ChromaDB   规则引擎   网络资讯
      │          │          │
      └──────────┴──────────┴────────────────
                           │
                  Human-in-the-loop
                  （LangGraph interrupt）
                           │
              ┌────────────────────────┐
              │       记忆与状态层        │
              │  短期记忆 · 长期记忆 · State │
              └────────────────────────┘
                           │
              ┌────────────────────────┐
              │    FastAPI + Gradio     │
              │      对外接口与前端       │
              └────────────────────────┘
```


---

## 🤖 Agent 详解

### 📊 数据分析 Agent
接收自然语言查询，自动生成 SQL 语句，查询玩家行为数据库（SQLite），输出数据结果与业务解读。

**支持问题示例：**
- 1月份各渠道的付费转化率是多少？
- VIP 等级最高的 5 个玩家总充值和购买次数分别是多少？
- 过去 30 天每周的新增注册玩家趋势如何？

**工具：** `query_game_data` · `get_table_schema`

---

### 🎮 玩家客服 Agent
基于 RAG 检索游戏知识库，回答玩家常见问题。当问题超出知识库范围或属于紧急情况时，自动创建结构化工单，并将本次记录写入长期记忆。

**支持问题示例：**
- 我充值了 648 元但钻石没到账怎么办？
- 我的账号被盗了，道具全没了！
- 月卡购买后为什么没有生效？

**工具：** `search_knowledge_base` · `create_ticket` · `get_player_history` · `save_contact_record`

---

### ✍️ 内容生成 Agent
生成游戏公告、活动文案等运营内容。内置合规检查工具自动过滤违禁词，支持 **Human-in-the-loop** 审批节点——图在此暂停，等待人工反馈，根据意见迭代修改直至通过。

**支持任务示例：**
- 写一篇五一劳动节活动公告，5 月 1 日至 5 月 7 日
- 生成春节版本更新说明，新增限定皮肤和春节活动副本

**工具：** `check_content_policy`

---

### 🔍 技术调研 Agent
调用 Tavily 搜索引擎获取行业资讯，内置**搜索质量自评**工具——若结果不足则自动优化关键词重新搜索，最终整理成结构化调研报告。

**支持任务示例：**
- 调研 2024 年游戏行业 AI NPC 的最新进展
- LangGraph 和 AutoGen 在多 Agent 编排上有什么区别？

**工具：** `search_web` · `evaluate_search_quality`

---

## 📁 项目结构

```
gameops-agent/
├── start.py                      # 一键启动脚本
├── main.py                       # 命令行入口
├── .env                          # 环境变量（不提交 Git）
├── .gitignore
├── requirements.txt
│
├── api/
│   ├── __init__.py
│   └── main.py                   # FastAPI 后端接口
│
├── ui/
│   ├── __init__.py
│   └── app.py                    # Gradio 前端界面
│
├── agents/
│   ├── __init__.py
│   ├── supervisor/
│   │   ├── __init__.py
│   │   └── graph.py              # Supervisor 主控图
│   ├── data_analyst/
│   │   ├── __init__.py
│   │   └── agent.py              # 数据分析 Agent
│   ├── customer_service/
│   │   ├── __init__.py
│   │   ├── build_vectorstore.py  # 构建 RAG 向量库（运行一次）
│   │   └── agent.py              # 客服 Agent
│   ├── content_generator/
│   │   ├── __init__.py
│   │   └── agent.py              # 内容生成 Agent（含 HitL）
│   └── tech_researcher/
│       ├── __init__.py
│       └── agent.py              # 技术调研 Agent
│
├── memory/
│   ├── __init__.py
│   └── player_memory.py          # 长期记忆管理
│
├── data/
│   ├── game_data.db              # 玩家行为数据库（SQLite）
│   ├── vectorstore/              # ChromaDB 向量库（自动生成）
│   └── player_profiles.json      # 玩家长期记忆（自动生成）
│
└── knowledge_base/
    └── game_faq.md               # 游戏客服知识库文档
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- OpenAI API Key（必须）
- Tavily API Key（可选，技术调研 Agent 需要）
- LangSmith API Key（可选，链路追踪）

### 1. 克隆项目

```bash
git clone https://github.com/your-username/gameops-agent.git
cd gameops-agent
```

### 2. 创建虚拟环境

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 一键启动

```bash
python start.py
```

首次运行会提示填写 API Key，自动保存到 `.env`，之后直接启动无需再次输入。

启动成功后：

| 服务 | 地址 |
|------|------|
| Gradio 前端 | http://127.0.0.1:7860 |
| FastAPI 文档 | http://127.0.0.1:8000/docs |
| LangSmith | https://smith.langchain.com |

---

## 🔧 手动启动

如需分开启动两个服务：

```bash
# 终端一：FastAPI 后端
uvicorn api.main:app --reload --port 8000

# 终端二：Gradio 前端
python ui/app.py
```

---

## 📦 依赖列表

```
langchain
langchain-openai
langchain-community
langchain-chroma
langchain-tavily
langgraph
chromadb
fastapi
uvicorn
gradio
python-dotenv
pandas
pydantic
```

安装：

```bash
pip install -r requirements.txt
```

---

## 🔑 环境变量说明

在项目根目录创建 `.env` 文件（或通过 `python start.py` 自动引导创建）：

```env
# 必填
OPENAI_API_KEY=sk-...

# 可选：LangSmith 链路追踪
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=gameops-agent

# 可选：技术调研 Agent
TAVILY_API_KEY=tvly-...
```

---

## 🧪 功能演示

启动后在 Gradio 界面依次输入以下问题，验证各 Agent 路由是否正确：

```
# 数据分析 Agent
1月份各渠道的付费转化率是多少？

# 客服 Agent
我是玩家1001，充值了648元但钻石没到账

# 客服 Agent（记忆功能）
我是玩家1001，上次充值问题还没有解决

# 内容生成 Agent
帮我写一篇五一劳动节活动公告，活动时间5月1日至5月7日，登录送限定皮肤

# 技术调研 Agent
调研一下2024年游戏行业AI NPC的最新进展
```

---

## 📊 技术选型说明

| 技术 | 用途 | 选择原因 |
|------|------|---------|
| LangGraph | Agent 工作流编排 | 原生支持状态管理、条件路由、Human-in-the-loop |
| LangChain | 工具链与模型集成 | 丰富的工具生态，与 LangGraph 深度集成 |
| ChromaDB | 向量数据库 | 本地部署零成本，适合原型开发 |
| SQLite | 玩家数据存储 | 轻量无需部署，适合模拟数据场景 |
| Tavily | 网络搜索 | LangChain 官方推荐，有免费额度 |
| FastAPI | 后端接口 | 高性能异步框架，自动生成 API 文档 |
| Gradio | 前端界面 | 快速构建 AI Demo，无需前端开发经验 |
| LangSmith | 可观测性 | 官方监控平台，可视化 Trace 与评测 |

---

## 🗺️ 后续规划

- [ ] 接入 Redis 替换 JSON 文件实现真正的分布式长期记忆
- [ ] 数据分析 Agent 增加 Python REPL 工具，支持自动生成图表
- [ ] 增加 Dify 工作流对比实验，对比 LangGraph 与 Dify 的优劣
- [ ] 接入 Docker 实现容器化部署
- [ ] 增加 Agent 效果评测模块，量化 RAG 召回准确率

---
---
<div align="center">

**如果这个项目对你有帮助，欢迎 Star ⭐**

</div>
