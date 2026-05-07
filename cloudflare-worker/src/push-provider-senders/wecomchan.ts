import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson, providerErrorResult } from "../push-http";
import { getWecomToken } from "../push-provider-auth";

export async function sendWecomChan(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  try {
    const token = await getWecomToken(
      provider.config.corpid,
      provider.config.secret,
      timeoutSec
    );
    const url = `https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${token}`;
    const payload = {
      touser: provider.config.touser || "@all",
      msgtype: "text",
      agentid: parseInt(provider.config.agentid, 10),
      text: {
        content: `${message.title}\n\n${message.body}\n\n${message.markdown}`,
      },
      safe: 0,
    };
    return postJson(provider, url, payload, timeoutSec);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
