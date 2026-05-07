import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";
import { appendDingTalkSign } from "../push-provider-auth";

export async function sendDingTalkBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const webhook = await appendDingTalkSign(
    provider.config.webhook,
    provider.config.secret || ""
  );
  const payload = {
    msgtype: "markdown",
    markdown: { title: message.title, text: message.markdown },
  };
  return postJson(provider, webhook, payload, timeoutSec);
}
