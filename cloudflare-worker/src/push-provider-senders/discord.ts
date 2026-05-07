import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import { providerErrorResult, readResponsePayload, resultFromParsedResponse } from "../push-http";

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
          content: `${message.title}\n\n${message.markdown}`,
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
