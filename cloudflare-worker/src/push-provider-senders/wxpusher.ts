import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { postJson } from "../push-http";
import { splitCsv } from "./common";

export async function sendWxPusher(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    appToken: provider.config.app_token,
    content: message.markdown,
    summary: message.title,
    contentType: 3,
  };
  const uids = splitCsv(provider.config.uids);
  const topicIds = splitCsv(provider.config.topic_ids);
  if (uids.length > 0) payload.uids = uids;
  if (topicIds.length > 0) {
    payload.topicIds = topicIds.map((id) => (/^\d+$/.test(id) ? parseInt(id, 10) : id));
  }
  return postJson(
    provider,
    "https://wxpusher.zjiecode.com/api/send/message",
    payload,
    timeoutSec,
    { successCodes: new Set([1000, "1000", 0, "0"]) }
  );
}
