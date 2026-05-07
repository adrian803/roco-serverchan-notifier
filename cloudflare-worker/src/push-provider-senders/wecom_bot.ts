import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";

export async function sendWecomBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  let webhook = (provider.config.webhook || "").trim();
  if (!webhook) {
    const key = (provider.config.key || "").trim();
    if (!key) {
      return {
        providerId: provider.id,
        providerName: provider.name,
        providerType: provider.type,
        success: false,
        message: "缺少 webhook 或 key",
        statusCode: null,
      };
    }
    webhook = `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=${key}`;
  }
  const payload = {
    msgtype: "markdown",
    markdown: { content: message.markdown },
  };
  return postJson(provider, webhook, payload, timeoutSec);
}
