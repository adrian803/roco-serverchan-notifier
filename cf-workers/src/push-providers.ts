import type { NotificationMessage, ProviderConfig, PushResult } from "./types";
import { providerRequiredFields } from "./provider-specs";
import { fetchWithTimeout } from "./rocom-client";
import { redactSensitiveText } from "./push-redaction";
import {
  postJson,
  providerErrorResult,
  readResponsePayload,
  resultFromParsedResponse,
} from "./push-http";
import {
  appendDingTalkSign,
  feishuSign,
  getWecomToken,
} from "./push-provider-auth";

type Sender = (
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
) => Promise<PushResult>;

function splitCsv(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function missingRequired(provider: ProviderConfig): string[] {
  return [...providerRequiredFields(provider.type)].filter(
    (name) => !(provider.config[name] || "").trim()
  );
}

async function sendServerChan(
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

async function sendPushPlus(
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

async function sendWecomChan(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  try {
    const token = await getWecomToken(
      provider.config.corpid,
      provider.config.secret,
      timeoutSec
    );
    const url = `https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${token}`;
    const payload = {
      touser: provider.config.touser || "@all",
      msgtype: "text",
      agentid: parseInt(provider.config.agentid, 10),
      text: {
        content: `${message.title}\n\n${message.body}\n\n${message.markdown}`,
      },
      safe: 0,
    };
    return postJson(provider, url, payload, timeoutSec);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}

async function sendWecomBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  let webhook = (provider.config.webhook || "").trim();
  if (!webhook) {
    const key = (provider.config.key || "").trim();
    if (!key) {
      return {
        providerId: provider.id,
        providerName: provider.name,
        providerType: provider.type,
        success: false,
        message: "缺少 webhook 或 key",
        statusCode: null,
      };
    }
    webhook = `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=${key}`;
  }
  const payload = {
    msgtype: "markdown",
    markdown: { content: message.markdown },
  };
  return postJson(provider, webhook, payload, timeoutSec);
}

async function sendWxPusher(
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

async function sendBark(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const serverUrl = (provider.config.server_url || "https://api.day.app").replace(
    /\/$/,
    ""
  );
  const url = `${serverUrl}/${provider.config.device_key}`;
  const payload: Record<string, unknown> = {
    title: message.title,
    body: `${message.body}\n\n${message.markdown}`,
  };
  const group = (provider.config.group || "").trim();
  if (group) payload.group = group;
  return postJson(provider, url, payload, timeoutSec, {
    successCodes: new Set([200, "200", 0, "0"]),
  });
}

async function sendDingTalkBot(
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

async function sendFeishuBot(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    msg_type: "post",
    content: {
      post: {
        zh_cn: {
          title: message.title,
          content: [
            [{ tag: "text", text: `${message.body}\n\n${message.markdown}` }],
          ],
        },
      },
    },
  };
  const secret = (provider.config.secret || "").trim();
  if (secret) {
    const timestamp = Math.floor(Date.now() / 1000).toString();
    payload.timestamp = timestamp;
    payload.sign = await feishuSign(secret, timestamp);
  }
  return postJson(provider, provider.config.webhook, payload, timeoutSec);
}

async function sendNtfy(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = (provider.config.base_url || "https://ntfy.sh").replace(
    /\/$/,
    ""
  );
  const url = `${baseUrl}/${provider.config.topic}`;
  const headers: Record<string, string> = {
    Title: message.title,
    Markdown: "yes",
  };
  for (const [cfgKey, headerName] of [
    ["priority", "Priority"],
    ["tags", "Tags"],
  ] as const) {
    const v = (provider.config[cfgKey] || "").trim();
    if (v) headers[headerName] = v;
  }
  const token = (provider.config.token || "").trim();
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
    const success = resp.status >= 200 && resp.status < 300;
    const text = (await resp.text()).slice(0, 200) || resp.statusText;
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success,
      message: text,
      statusCode: resp.status,
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null,
    };
  }
}

async function sendGotify(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = (provider.config.base_url || "").replace(/\/$/, "");
  const appToken = encodeURIComponent(provider.config.app_token);
  const url = `${baseUrl}/message?token=${appToken}`;
  const priority = parseInt(provider.config.priority || "5", 10) || 5;
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
    const success = resp.status >= 200 && resp.status < 300;
    const text = (await resp.text()).slice(0, 200) || resp.statusText;
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success,
      message: text,
      statusCode: resp.status,
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null,
    };
  }
}

const PROVIDER_SENDERS: Record<string, Sender> = {
  serverchan: sendServerChan,
  pushplus: sendPushPlus,
  wecomchan: sendWecomChan,
  wecom_bot: sendWecomBot,
  wxpusher: sendWxPusher,
  bark: sendBark,
  dingtalk_bot: sendDingTalkBot,
  feishu_bot: sendFeishuBot,
  ntfy: sendNtfy,
  gotify: sendGotify,
};

export async function sendProvider(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const missing = missingRequired(provider);
  if (missing.length > 0) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `缺少配置: ${missing.join(", ")}`,
      statusCode: null,
    };
  }

  const sender = PROVIDER_SENDERS[provider.type];
  if (!sender) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `未知通道类型: ${provider.type}`,
      statusCode: null,
    };
  }

  try {
    const result = await sender(provider, message, timeoutSec);
    return {
      ...result,
      message: redactSensitiveText(provider, result.message),
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: redactSensitiveText(provider, String(err)),
      statusCode: null,
    };
  }
}
