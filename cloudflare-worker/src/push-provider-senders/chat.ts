import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import { postJson, providerErrorResult, readResponsePayload, resultFromParsedResponse } from "../push-http";

function chatText(message: NotificationMessage): string {
  return `${message.title}\n\n${message.markdown}`;
}

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
      text: chatText(message),
    },
    timeoutSec
  );
}

export async function sendDiscord(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const webhook = provider.config.webhook;
  const separator = webhook.includes("?") ? "&" : "?";

  try {
    const resp = await fetchWithTimeout(
      `${webhook}${separator}wait=true`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: chatText(message),
          allowed_mentions: { parse: [] },
        }),
      },
      timeoutSec
    );

    const { payload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(
      provider,
      resp,
      payload,
      text,
      new Set([null, undefined])
    );
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
