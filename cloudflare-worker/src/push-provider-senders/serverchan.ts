import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import { providerErrorResult, readResponsePayload, resultFromParsedResponse } from "../push-http";

export async function sendServerChan(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const sendkey = provider.config.sendkey;
  const url = `https://sctapi.ftqq.com/${sendkey}.send`;
  const body = new URLSearchParams({
    title: message.title,
    desp: message.markdown,
  });

  try {
    const resp = await fetchWithTimeout(
      url,
      { method: "POST", body },
      timeoutSec
    );
    const successCodes = new Set([0, "0", null, undefined]);
    const { payload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(provider, resp, payload, text, successCodes);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
