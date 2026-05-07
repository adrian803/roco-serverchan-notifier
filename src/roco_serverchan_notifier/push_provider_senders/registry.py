from __future__ import annotations

from .bark import send_bark
from .discord import send_discord
from .dingtalk_bot import send_dingtalk_bot
from .feishu_bot import send_feishu_bot
from .gotify import send_gotify
from .ntfy import send_ntfy
from .pushplus import send_pushplus
from .serverchan import send_serverchan
from .telegram import send_telegram
from .wecom_bot import send_wecom_bot
from .wecomchan import send_wecomchan
from .wxpusher import send_wxpusher


PROVIDER_SENDERS = {
    "serverchan": send_serverchan,
    "pushplus": send_pushplus,
    "telegram": send_telegram,
    "discord": send_discord,
    "wecomchan": send_wecomchan,
    "wecom_bot": send_wecom_bot,
    "wxpusher": send_wxpusher,
    "bark": send_bark,
    "dingtalk_bot": send_dingtalk_bot,
    "feishu_bot": send_feishu_bot,
    "ntfy": send_ntfy,
    "gotify": send_gotify,
}
