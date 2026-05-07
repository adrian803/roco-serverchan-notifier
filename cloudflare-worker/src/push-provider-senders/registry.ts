import type { Sender } from "./common";
import { sendBark } from "./bark";
import { sendDiscord } from "./discord";
import { sendDingTalkBot } from "./dingtalk_bot";
import { sendFeishuBot } from "./feishu_bot";
import { sendGotify } from "./gotify";
import { sendNtfy } from "./ntfy";
import { sendPushPlus } from "./pushplus";
import { sendServerChan } from "./serverchan";
import { sendTelegram } from "./telegram";
import { sendWecomBot } from "./wecom_bot";
import { sendWecomChan } from "./wecomchan";
import { sendWxPusher } from "./wxpusher";

export const PROVIDER_SENDERS: Record<string, Sender> = {
  serverchan: sendServerChan,
  pushplus: sendPushPlus,
  telegram: sendTelegram,
  discord: sendDiscord,
  wecomchan: sendWecomChan,
  wecom_bot: sendWecomBot,
  wxpusher: sendWxPusher,
  bark: sendBark,
  dingtalk_bot: sendDingTalkBot,
  feishu_bot: sendFeishuBot,
  ntfy: sendNtfy,
  gotify: sendGotify,
};
