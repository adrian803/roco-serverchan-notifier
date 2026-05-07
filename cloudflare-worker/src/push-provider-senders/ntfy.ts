import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import { providerErrorResult, resultFromParsedResponse } from "../push-http";
import { providerConfigText } from "./common";

export async function sendNtfy(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = providerConfigText(provider, "base_url").replace(/\/$/, "");
  const url = `${baseUrl}/${provider.config.topic}`;
  const headers: Record<string, string> = {
    Title: message.title,
    Markdown: "yes",
  };
  for (const [cfgKey, headerName] of [
    ["priority", "Priority"],
    ["tags", "Tags"],
  ] as const) {
    const v = providerConfigText(provider, cfgKey);
    if (v) headers[headerName] = v;
  }
  const token = providerConfigText(provider, "token");
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers,
        body: message.markdown,
      },
      timeoutSec
    );
    const text = await resp.text();
    return resultFromParsedResponse(
      provider,
      resp,
      {},
      text,
      new Set([null, undefined])
    );
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
