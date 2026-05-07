import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import { providerErrorResult, readResponsePayload, resultFromParsedResponse } from "../push-http";
import { providerConfigText } from "./common";

export async function sendGotify(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = (provider.config.base_url || "").replace(/\/$/, "");
  const appToken = encodeURIComponent(provider.config.app_token);
  const url = `${baseUrl}/message?token=${appToken}`;
  const priority = parseInt(providerConfigText(provider, "priority"), 10) || 5;
  const payload = {
    title: message.title,
    message: message.markdown,
    priority,
  };

  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      timeoutSec
    );
    const { payload: respPayload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(
      provider,
      resp,
      respPayload,
      text,
      new Set([null, undefined])
    );
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
