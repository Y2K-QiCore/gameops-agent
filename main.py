from langchain_core.messages import HumanMessage
from agents.supervisor.graph import supervisor_graph

def main():
    config = {"configurable": {"thread_id": "session-001"}}
    print("="*50)
    print("  GameOps-Agent 已启动")
    print("  输入 quit 退出")
    print("="*50)

    while True:
        user_input = input("\n你：").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break

        result = supervisor_graph.invoke(
            {
                "messages":   [HumanMessage(content=user_input)],
                "next_agent": "",
            },
            config=config,
        )

        # 取最后一条 AI 回复打印
        last = result["messages"][-1].content
        print(f"\nAgent：{last}")

if __name__ == "__main__":
    main()