import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";
import { providerConfigText } from "./common";

export async function sendBark(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const serverUrl = providerConfigText(provider, "server_url").replace(/\/$/, "");
  const url = `${serverUrl}/${provider.config.device_key}`;
  const payload: Record<string, unknown> = {
    title: message.title,
    body: `${message.body}\n\n${message.markdown}`,
  };
  const group = providerConfigText(provider, "group");
  if (group) payload.group = group;
  return postJson(provider, url, payload, timeoutSec, {
    successCodes: new Set([200, "200", 0, "0"]),
  });
}
