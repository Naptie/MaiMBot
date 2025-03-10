import asyncio
from datetime import datetime
import math
from random import random
from .config import global_config


class WillingManager:
    def __init__(self):
        self.group_reply_willing = {}  # 存储每个群的回复意愿
        self.group_last_reply_time = {}  # 存储每个群的最后回复时间
        self._decay_task = None
        self._started = False

    async def _decay_reply_willing(self):
        """定期衰减回复意愿"""
        while True:
            await asyncio.sleep(5)
            for group_id in self.group_reply_willing:
                self.group_reply_willing[group_id] = max(
                    0, self.group_reply_willing[group_id] * 0.75
                )

    def get_willing(self, group_id: int) -> float:
        """获取指定群组的回复意愿"""
        return self.group_reply_willing.get(group_id, 0)

    def set_willing(self, group_id: int, willing: float):
        """设置指定群组的回复意愿"""
        self.group_reply_willing[group_id] = willing

    def change_reply_willing_received(
        self,
        group_id: int,
        topic: str,
        is_mentioned_bot: bool,
        config,
        user_id: int = None,
        is_emoji: bool = False,
        interested_rate: float = 0,
    ) -> float:
        """改变指定群组的回复意愿并返回回复概率与是否回复"""
        current_willing = self.group_reply_willing.get(group_id, 0)

        # print(f"初始意愿: {current_willing}")
        if is_mentioned_bot and current_willing < 1.0:
            current_willing += 0.94
            print(f"被提及, 当前意愿: {current_willing}")
        elif is_mentioned_bot:
            current_willing += 0.05
            print(f"被重复提及, 当前意愿: {current_willing}")

        if is_emoji:
            current_willing *= 0.1
            print(f"表情包, 当前意愿: {current_willing}")

        print(
            f"放大系数 interested_rate: {global_config.response_interested_rate_amplifier}"
        )
        interested_rate *= (
            global_config.response_interested_rate_amplifier
        )  # 放大回复兴趣度
        if interested_rate > 0.4:
            # print(f"兴趣度: {interested_rate}, 当前意愿: {current_willing}")
            current_willing += interested_rate - 0.4

        current_willing *= global_config.response_willing_amplifier  # 放大回复意愿
        # print(f"放大系数_willing: {global_config.response_willing_amplifier}, 当前意愿: {current_willing}")

        x = datetime.now().timestamp() - self.group_last_reply_time.get(group_id, 0)
        rate_limit_factor = (
            math.atan(
                (x - 40) / 3
                if group_id in config.talk_frequency_down_groups
                else (x - 10) / 3
            )
            / math.pi
            + 0.5
        )
        current_willing *= rate_limit_factor
        print(f"限制系数: {rate_limit_factor:.4f}, 当前意愿: {current_willing:.4f}")

        reply_probability = max((current_willing - 0.45) * 2, 0)
        if group_id not in config.talk_allowed_groups:
            current_willing = 0
            reply_probability = 0

        if not is_mentioned_bot and group_id in config.talk_frequency_down_groups:
            reply_probability = reply_probability / global_config.down_frequency_rate

        reply_probability = min(reply_probability, 1)
        if reply_probability < 0:
            reply_probability = 0

        self.group_reply_willing[group_id] = min(current_willing, 3.0)

        do_reply = random() < reply_probability
        if do_reply:
            self.update_last_reply_time(group_id)
        return reply_probability, do_reply

    def change_reply_willing_sent(self, group_id: int):
        """开始思考后降低群组的回复意愿"""
        current_willing = self.group_reply_willing.get(group_id, 0)
        self.group_reply_willing[group_id] = max(0, current_willing - 2)

    def change_reply_willing_after_sent(self, group_id: int):
        """发送消息后提高群组的回复意愿"""
        current_willing = self.group_reply_willing.get(group_id, 0)
        if current_willing < 1:
            self.group_reply_willing[group_id] = min(1, current_willing + 0.2)

    def update_last_reply_time(self, group_id: int):
        """更新群组的最后回复时间"""
        self.group_last_reply_time[group_id] = datetime.now().timestamp()

    async def ensure_started(self):
        """确保衰减任务已启动"""
        if not self._started:
            if self._decay_task is None:
                self._decay_task = asyncio.create_task(self._decay_reply_willing())
            self._started = True


# 创建全局实例
willing_manager = WillingManager()
