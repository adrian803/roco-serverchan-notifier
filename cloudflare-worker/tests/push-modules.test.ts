import assert from "node:assert/strict";
import { test } from "node:test";

import { deliverySummary } from "../src/push-delivery";
import { PROVIDER_TYPES } from "../src/provider-specs";
import { clearWecomTokenCache, getWecomToken } from "../src/push-provider-auth";
import { postJson } from "../src/push-http";
import { redactSensitiveText } from "../src/push-redaction";
import { sendProvider } from "../src/push-providers";
import { PROVIDER_SENDERS } from "../src/push-provider-senders/registry";
import { sendDiscord, sendTelegram } from "../src/push-provider-senders/chat";
import { sendPushPlus } from "../src/push-provider-senders/token";
import { sendDingTalkBot } from "../src/push-provider-senders/webhook";
import { sendWecomChan } from "../src/push-provider-senders/wecom";
import type { DeliveryReport, NotificationMessage, ProviderConfig } from "../src/types";

test("split push modules expose delivery, redaction, and provider boundaries", async () => {
  const report: DeliveryReport = { success: true, mode: "all", results: [] };
  const provider: ProviderConfig = {
    id: "p1",
    type: "serverchan",
    name: "Server 酱",
    enabled: true,
    config: { sendkey: "secret-send-key" },
  };
  const message: NotificationMessage = {
    title: "标题",
    body: "摘要",
    markdown: "正文",
  };

  assert.equal(deliverySummary(report), "没有可用推送通道");
  assert.equal(redactSensitiveText(provider, "secret-send-key"), "[已脱敏]");
  assert.equal(typeof sendProvider, "function");
  assert.equal(message.title, "标题");
});

test("provider senders are grouped by family modules", () => {
  assert.deepEqual(Object.keys(PROVIDER_SENDERS), Object.keys(PROVIDER_TYPES));
  assert.equal(PROVIDER_SENDERS.pushplus, sendPushPlus);
  assert.equal(PROVIDER_SENDERS.telegram, sendTelegram);
  assert.equal(PROVIDER_SENDERS.discord, sendDiscord);
  assert.equal(PROVIDER_SENDERS.dingtalk_bot, sendDingTalkBot);
  assert.equal(PROVIDER_SENDERS.wecomchan, sendWecomChan);
});

test("provider required validation accepts manifest defaults", async () => {
  const originalFetch = globalThis.fetch;
  let sentUrl = "";
  globalThis.fetch = async (input) => {
    sentUrl = String(input);
    return new Response(JSON.stringify({ code: 0 }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const provider: ProviderConfig = {
      id: "p1",
      type: "bark",
      name: "Bark",
      enabled: true,
      config: { device_key: "device-key" },
    };
    const message: NotificationMessage = {
      title: "标题",
      body: "摘要",
      markdown: "正文",
    };

    const result = await sendProvider(provider, message, 30);

    assert.equal(result.success, true);
    assert.equal(sentUrl, "https://api.day.app/device-key");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("push-http preserves non-json error bodies and redacts provider secrets", async () => {
  const originalFetch = globalThis.fetch;
  const provider: ProviderConfig = {
    id: "p1",
    type: "pushplus",
    name: "PushPlus",
    enabled: true,
    config: { token: "secret-token" },
  };
  globalThis.fetch = async () =>
    new Response("bad token=abc secret-token", {
      status: 500,
      statusText: "Internal Server Error",
    });

  try {
    const result = await postJson(provider, "https://example.com/send", {}, 30);

    assert.equal(result.success, false);
    assert.equal(result.statusCode, 500);
    assert.equal(result.message, "bad token=[已脱敏] [已脱敏]");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("push-http supports Telegram ok and description fields", async () => {
  const originalFetch = globalThis.fetch;
  const provider: ProviderConfig = {
    id: "telegram-env",
    type: "telegram",
    name: "Telegram",
    enabled: true,
    config: { bot_token: "bot-token", chat_id: "-100123" },
  };
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ ok: true, result: { message_id: 1 } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  try {
    const result = await sendProvider(
      provider,
      { title: "标题", body: "摘要", markdown: "正文" },
      30
    );

    assert.equal(result.success, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("telegram sender posts expected payload", async () => {
  const originalFetch = globalThis.fetch;
  let receivedUrl = "";
  let receivedBody = "";
  globalThis.fetch = async (input, init) => {
    receivedUrl = String(input);
    receivedBody = String(init?.body || "");
    return new Response(JSON.stringify({ ok: true, result: { message_id: 1 } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const provider: ProviderConfig = {
      id: "telegram-env",
      type: "telegram",
      name: "Telegram",
      enabled: true,
      config: { bot_token: "bot-token", chat_id: "-1001234567890" },
    };

    const result = await sendProvider(
      provider,
      { title: "标题", body: "摘要", markdown: "正文" },
      30
    );

    assert.equal(result.success, true);
    assert.equal(receivedUrl, "https://api.telegram.org/botbot-token/sendMessage");
    assert.deepEqual(JSON.parse(receivedBody), {
      chat_id: "-1001234567890",
      text: "标题\n\n正文",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("discord sender posts expected payload and redacts webhook errors", async () => {
  const originalFetch = globalThis.fetch;
  let receivedUrl = "";
  let receivedBody = "";
  globalThis.fetch = async (input, init) => {
    receivedUrl = String(input);
    receivedBody = String(init?.body || "");
    return new Response(
      "webhook=https://discord.com/api/webhooks/123/secret",
      {
        status: 500,
        statusText: "Internal Server Error",
      }
    );
  };

  try {
    const provider: ProviderConfig = {
      id: "discord-env",
      type: "discord",
      name: "Discord",
      enabled: true,
      config: { webhook: "https://discord.com/api/webhooks/123/secret" },
    };

    const result = await sendProvider(
      provider,
      { title: "标题", body: "摘要", markdown: "正文" },
      30
    );

    assert.equal(receivedUrl, "https://discord.com/api/webhooks/123/secret?wait=true");
    assert.deepEqual(JSON.parse(receivedBody), {
      content: "标题\n\n正文",
      allowed_mentions: { parse: [] },
    });
    assert.equal(result.success, false);
    assert.match(result.message, /\[已脱敏\]/);
    assert.doesNotMatch(result.message, /discord\.com\/api\/webhooks\/123\/secret/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("push-provider-auth caches WeCom tokens", async () => {
  const originalFetch = globalThis.fetch;
  let tokenFetches = 0;
  clearWecomTokenCache();
  globalThis.fetch = async () => {
    tokenFetches += 1;
    return new Response(
      JSON.stringify({ errcode: 0, access_token: "token-value", expires_in: 7200 }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    const first = await getWecomToken("corp", "secret", 30);
    const second = await getWecomToken("corp", "secret", 30);

    assert.equal(first, "token-value");
    assert.equal(second, "token-value");
    assert.equal(tokenFetches, 1);
  } finally {
    clearWecomTokenCache();
    globalThis.fetch = originalFetch;
  }
});
