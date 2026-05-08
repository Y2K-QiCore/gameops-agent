"""
长期记忆层：跨会话存储玩家档案和历史投诉记录。
用 JSON 文件模拟 Redis 的 KV 存储，原理一致，省去部署成本。
"""
import json
from pathlib import Path
from datetime import datetime

PROFILES_PATH = Path(__file__).parent.parent / "data" / "player_profiles.json"


class PlayerMemory:
    def __init__(self):
        self._load()

    def _load(self):
        if PROFILES_PATH.exists():
            with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                self.profiles = json.load(f)
        else:
            self.profiles = {}

    def _save(self):
        PROFILES_PATH.parent.mkdir(exist_ok=True)
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump(self.profiles, f, ensure_ascii=False, indent=2)

    def get_profile(self, player_id: str) -> dict:
        """获取玩家历史档案，没有则返回空 dict"""
        return self.profiles.get(str(player_id), {})

    def record_contact(self, player_id: str, issue: str):
        """记录一次玩家联系客服的记录"""
        pid = str(player_id)
        if pid not in self.profiles:
            self.profiles[pid] = {
                "player_id":     pid,
                "contact_count": 0,
                "history":       [],
            }
        self.profiles[pid]["contact_count"] += 1
        self.profiles[pid]["last_contact"]   = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.profiles[pid]["history"].append({
            "time":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "issue": issue,
        })
        # 只保留最近 10 条记录，避免文件膨胀
        self.profiles[pid]["history"] = self.profiles[pid]["history"][-10:]
        self._save()

    def summary(self, player_id: str) -> str:
        """返回玩家记忆摘要字符串，供 LLM 读取"""
        profile = self.get_profile(player_id)
        if not profile:
            return f"玩家 {player_id} 没有历史联系记录。"

        lines = [
            f"玩家 {player_id} 历史记录：",
            f"  累计联系次数：{profile.get('contact_count', 0)} 次",
            f"  最近联系时间：{profile.get('last_contact', '未知')}",
            "  历史问题：",
        ]
        for h in profile.get("history", [])[-3:]:  # 只展示最近3条给LLM
            lines.append(f"    [{h['time']}] {h['issue']}")
        return "\n".join(lines)


# 单例，整个项目共用一个实例
player_memory = PlayerMemory()