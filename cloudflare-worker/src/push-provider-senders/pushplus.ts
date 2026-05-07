import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";

export async function sendPushPlus(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    token: provider.config.token,
    title: message.title,
    content: message.markdown,
    template: "markdown",
  };
  for (const key of ["topic", "channel"]) {
    const v = (provider.config[key] || "").trim();
    if (v) payload[key] = v;
  }
  return postJson(provider, "https://www.pushplus.plus/send", payload, timeoutSec, {
    successCodes: new Set([200, "200", 0, "0"]),
  });
}
