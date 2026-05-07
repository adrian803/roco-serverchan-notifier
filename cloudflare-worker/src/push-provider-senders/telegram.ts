import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";

export async function sendTelegram(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  return postJson(
    provider,
    `https://api.telegram.org/bot${provider.config.bot_token}/sendMessage`,
    {
      chat_id: provider.config.chat_id,
      text: `${message.title}\n\n${message.markdown}`,
    },
    timeoutSec
  );
}
