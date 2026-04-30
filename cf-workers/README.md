# roco-push-worker

[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare%20Workers-_worker.js-F6821F?logo=cloudflare&logoColor=white)](_worker.js)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](../LICENSE)

《洛克王国世界》远行商人推送服务的 Cloudflare Workers 版本。默认使用 Cron Triggers 定时执行，无需服务器，免费计划通常足够本项目每天 4 次调度。

本目录同时支持两种部署方式：

| 方式 | 适合人群 | 是否需要本地 Node.js | 配置位置 |
|---|---|:---:|---|
| 控制台粘贴 `_worker.js` | 普通使用者，最快部署 | 否 | Cloudflare Dashboard |
| Wrangler 项目部署 | 维护者，需要源码、CI、可重复部署 | 是 | `wrangler.toml` + secrets |

建议普通用户优先使用控制台粘贴；项目维护、二次开发或自动化发布时使用 Wrangler 项目部署。两种方式使用同一份 TypeScript 源码，`_worker.js` 是从 `src/` 构建出的可粘贴产物。

## 目录

- [与 Docker 版的对比](#与-docker-版的对比)
- [工作原理](#工作原理)
- [快速开始](#快速开始)
- [部署指南](#部署指南)
- [HTTP 端点](#http-端点)
- [Cron 调度](#cron-调度)
- [推送通道](#推送通道)
- [发送策略](#发送策略)
- [环境变量参考](#环境变量参考)
- [项目结构](#项目结构)
- [本地调试与维护](#本地调试与维护)
- [从其他部署方式迁移](#从其他部署方式迁移)
- [外部监控集成](#外部监控集成)
- [费用说明](#费用说明)
- [常见问题](#常见问题)
- [许可](#许可)

## 与 Docker 版的对比

| 特性 | Docker 版 | CF Workers 版 |
|------|----------|--------------|
| Web 控制台 | 有（页面管理配置） | 无（通过环境变量配置） |
| 定时触发 | 内置调度器 | CF Cron Triggers |
| 推送通道 | 10 种 | 10 种（完全一致） |
| 费用 | 服务器费用 | 免费（CF 免费计划通常足够） |
| 精确度 | 精确到秒 | 可能延迟 1-2 分钟 |
| 部署复杂度 | Docker + 服务器 | 控制台粘贴，或 Wrangler 项目部署 |
| 持久化 | `config.json` 文件 | 环境变量（无文件系统） |
| 最佳场景 | 长期运行、需要 Web 管理 | 免费托管、轻量运行 |

两个版本共享相同的推送逻辑和通道配置，可以根据需要选择或切换。

## 工作原理

```
┌─────────────────────────────────────────────────┐
│              Cloudflare Workers                  │
│                                                  │
│  Cron Trigger ──┐     HTTP Request ──┐          │
│  (每天4次定时)    │     (/trigger)     │          │
│                  ▼                    ▼          │
│            ┌──────────┐                         │
│            │ runPipeline│                        │
│            └─────┬─────┘                         │
│                  │                               │
│      ┌───────────┼───────────┐                   │
│      ▼           ▼           ▼                   │
│  fetchMerchant  process    sendDelivery          │
│  (获取数据)     (过滤活跃)   (推送到通道)           │
│      │           │           │                   │
│      ▼           ▼           ▼                   │
│  ROCOM API    真实 epoch    10 种推送通道          │
│  (数据源)     过滤+轮次      同时/单选/主备         │
└─────────────────────────────────────────────────┘
```

## 快速开始

### 前置条件

控制台粘贴部署只需要：

- [Cloudflare 账号](https://dash.cloudflare.com/)（免费即可）
- 已获取 `ROCOM_API_KEY`（参考 [数据源项目](https://github.com/Entropy-Increase-Team/)）
- 至少一个推送通道的 token / webhook，例如 `SERVERCHAN_SENDKEY`

只有在本地调试、重新生成 `_worker.js` 或使用 Wrangler 项目部署时，才需要 Node.js 18+。

### 方式 A：控制台粘贴 `_worker.js`（推荐普通用户）

1. 打开 Cloudflare Dashboard → Workers & Pages → Create Worker。
2. 进入 Worker 编辑器，删除默认代码。
3. 将 [_worker.js](_worker.js) 的完整内容粘贴进去，保存并部署。
4. 在 Settings → Variables and Secrets 中添加 `ROCOM_API_KEY` 和至少一个推送通道 secret。
5. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`。
6. 访问 `/health` 检查服务，访问 `/trigger` 手动触发一次。

部署后会按 Cron 自动运行，对应北京时间 08:05 / 12:05 / 16:05 / 20:05。

### 方式 B：Wrangler 项目部署（适合维护者）

Wrangler 方式适合需要从源码构建、接入 CI、统一管理 `wrangler.toml` 的场景。

```bash
cd cf-workers
npm ci
npx wrangler login

# 必需：数据源 Key
npx wrangler secret put ROCOM_API_KEY

# 至少配置一个推送通道，例如 Server 酱
npx wrangler secret put SERVERCHAN_SENDKEY

# 可选：保护 /trigger
npx wrangler secret put TRIGGER_TOKEN

# 部署 src/index.ts，并使用 wrangler.toml 中的 vars 和 cron
npm run deploy
```

使用 Wrangler 项目部署时，非敏感变量和 Cron 建议统一维护在 `wrangler.toml`。如果同时在 Dashboard 手动改同名配置，后续 `wrangler deploy` 可能覆盖这些差异。

## 部署指南

### 推荐选择

- 只是部署使用：用控制台粘贴 `_worker.js`，不需要安装 Node.js。
- 要改 TypeScript 源码：用 Wrangler 项目部署，并在改动后运行测试和构建检查。
- 要把源码改动同步给粘贴用户：运行 `npm run build:worker` 重新生成 `_worker.js`，并提交生成后的文件。

### 控制台变量配置

在 Worker 的 Settings → Variables and Secrets 中配置：

| 类型 | 必需 | 示例 |
|---|---|---|
| Secret | 是 | `ROCOM_API_KEY` |
| Secret | 至少一个 | `SERVERCHAN_SENDKEY`、`PUSHPLUS_TOKEN`、`DINGTALK_WEBHOOK` |
| Secret | 否 | `TRIGGER_TOKEN` |
| Variable | 否 | `DELIVERY_MODE`、`SELECTED_PROVIDER`、`FAILOVER_ORDER`、`NOTIFY_EMPTY` |

Secrets 用于 token、webhook、Key；Variables 用于非敏感开关和策略。

### Wrangler 项目配置

Wrangler 项目部署使用：

- `wrangler.toml`：Worker 名称、入口文件、Cron、非敏感 vars。
- `wrangler secret put <NAME>`：敏感字段。
- `.dev.vars`：本地调试专用，不提交。

常用命令：

```bash
cd cf-workers
npm test
npx tsc --noEmit
npm run dry-run
npm run deploy
npm run tail
```

### 自定义域名（可选）

控制台粘贴部署：在 Cloudflare Dashboard → Worker → Settings → Domains & Routes 中添加自定义域名或路由。

Wrangler 项目部署：也可以在 `wrangler.toml` 中配置 routes 后重新部署。

```toml
routes = [
  { pattern = "push.example.com/*", zone_name = "example.com" }
]
```

## HTTP 端点

| 路径 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查，返回 `{ ok: true, timestamp: "..." }` |
| `/trigger` | GET/POST | 手动触发一次完整推送流程，返回执行结果 |

`/trigger` 默认保持开放，便于迁移和外部手动触发。配置 `TRIGGER_TOKEN` secret 后，触发请求必须提供匹配 token；Cron Trigger 和 `/health` 不受影响。

```bash
# 健康检查
curl https://roco-push-worker.<子域>.workers.dev/health

# 开放模式
curl https://roco-push-worker.<子域>.workers.dev/trigger

# 配置 TRIGGER_TOKEN 后任选一种
curl "https://roco-push-worker.<子域>.workers.dev/trigger?token=你的token"
curl -H "X-Trigger-Token: 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
curl -H "Authorization: Bearer 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
```

返回示例：

```json
{ "exitCode": 0, "summary": "2/3 个通道成功" }
```

缺少配置时：

```json
{ "exitCode": 2, "summary": "缺少必要环境变量: ROCOM_API_KEY" }
```

## Cron 调度

默认每天北京时间 08:05、12:05、16:05、20:05 触发，即远行商人刷新后 5 分钟。

| 北京时间 | UTC 时间 | Cron 表达式 |
|:--------:|:--------:|:-----------:|
| 08:05 | 00:05 | `5 0 * * *` |
| 12:05 | 04:05 | `5 4 * * *` |
| 16:05 | 08:05 | `5 8 * * *` |
| 20:05 | 12:05 | `5 12 * * *` |

控制台粘贴部署：在 Dashboard → Worker → Triggers → Cron Triggers 中添加：

```cron
5 0,4,8,12 * * *
```

Wrangler 项目部署：在 `wrangler.toml` 中维护：

```toml
[triggers]
crons = ["5 0,4,8,12 * * *"]
```

Cloudflare Cron Triggers 不保证精确到秒，实际执行可能有延迟。免费计划的额度通常足够本项目默认每天 4 次调度，具体限制以 Cloudflare 官方文档为准。

## 推送通道

10 种推送通道，与 Docker 版完全一致：

| 通道 | 最少需要 | 说明 |
|------|---------|------|
| Server 酱 | `SERVERCHAN_SENDKEY` | 推送到微信 |
| PushPlus | `PUSHPLUS_TOKEN` | 支持群组、渠道 |
| 企业微信应用 | `WECOM_CORPID` + `WECOM_SECRET` + `WECOM_AGENTID` | 自动获取 access_token |
| 企业微信群机器人 | `WECOM_BOT_WEBHOOK` 或 `WECOM_BOT_KEY` | Markdown 消息 |
| WxPusher | `WXPUSHER_APP_TOKEN` | 支持 UID / Topic |
| Bark | `BARK_DEVICE_KEY` | 推送到 iOS |
| 钉钉群机器人 | `DINGTALK_WEBHOOK` | 可选加签 |
| 飞书群机器人 | `FEISHU_WEBHOOK` | 可选加签 |
| ntfy | `NTFY_TOPIC` | 可选 bearer token |
| Gotify | `GOTIFY_BASE_URL` + `GOTIFY_APP_TOKEN` | 可配优先级 |

控制台粘贴部署时，添加新通道只需要在 Worker 控制台增加对应 Secret/Variable。Wrangler 项目部署时，Secret 用 `wrangler secret put` 添加，非敏感变量写入 `wrangler.toml` 后重新部署。

## 发送策略

通过 `DELIVERY_MODE` 控制：

| 值 | 行为 |
|---|---|
| `all`（默认） | 并发向所有启用通道发送，至少一个成功即认为送达 |
| `single` | 只向 `SELECTED_PROVIDER` 指定的通道发送，未配置或无效时回退第一个启用通道 |
| `failover` | 按 `FAILOVER_ORDER` 指定顺序尝试通道，第一个成功后停止；未配置时按默认通道顺序 |

控制台粘贴部署：在 Worker 控制台的 Variables 中添加：

| 变量 | 示例 |
|------|------|
| `DELIVERY_MODE` | `failover` |
| `SELECTED_PROVIDER` | `serverchan-default` |
| `FAILOVER_ORDER` | `pushplus-env,serverchan-default` |

Wrangler 项目部署：在 `wrangler.toml` 中设置：

```toml
[vars]
DELIVERY_MODE = "failover"
SELECTED_PROVIDER = "serverchan-default"
FAILOVER_ORDER = "pushplus-env,serverchan-default"
```

可用通道 ID：

| 通道 | Provider ID |
|------|-------------|
| Server 酱 | `serverchan-default` |
| PushPlus | `pushplus-env` |
| 企业微信应用 | `wecomchan-env` |
| 企业微信群机器人 | `wecom-bot-env` |
| WxPusher | `wxpusher-env` |
| Bark | `bark-env` |
| 钉钉群机器人 | `dingtalk-env` |
| 飞书群机器人 | `feishu-env` |
| ntfy | `ntfy-env` |
| Gotify | `gotify-env` |

## 环境变量参考

### Secrets

| 变量 | 通道 | 说明 |
|------|------|------|
| `ROCOM_API_KEY` | 数据源 | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 | SendKey |
| `PUSHPLUS_TOKEN` | PushPlus | Token |
| `WECOM_CORPID` | 企业微信 | CorpID |
| `WECOM_SECRET` | 企业微信 | Secret |
| `WECOM_AGENTID` | 企业微信 | AgentID |
| `WECOM_BOT_WEBHOOK` | 企微群机器人 | Webhook URL |
| `WECOM_BOT_KEY` | 企微群机器人 | Key |
| `WXPUSHER_APP_TOKEN` | WxPusher | AppToken |
| `BARK_DEVICE_KEY` | Bark | Device Key |
| `DINGTALK_WEBHOOK` | 钉钉 | Webhook URL |
| `DINGTALK_SECRET` | 钉钉 | 加签密钥（可选） |
| `FEISHU_WEBHOOK` | 飞书 | Webhook URL |
| `FEISHU_SECRET` | 飞书 | 加签密钥（可选） |
| `NTFY_TOPIC` | ntfy | Topic |
| `NTFY_TOKEN` | ntfy | Bearer Token（可选） |
| `GOTIFY_APP_TOKEN` | Gotify | App Token |
| `TRIGGER_TOKEN` | 手动触发 | `/trigger` 手动触发 token（可选） |

### Variables

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `ROCOM_API_URL` | 内置默认 | 数据接口地址 |
| `NOTIFY_EMPTY` | `false` | 无商品时是否推送 |
| `DELIVERY_MODE` | `all` | 发送策略：`all` / `single` / `failover` |
| `SELECTED_PROVIDER` | 第一个启用通道 | `single` 模式使用的 provider id |
| `FAILOVER_ORDER` | 启用通道默认顺序 | `failover` 模式顺序，逗号分隔 provider id |
| `HTTP_TIMEOUT` | `30` | 请求超时秒数 |
| `PUSHPLUS_TOPIC` | 空 | PushPlus 群组编码 |
| `PUSHPLUS_CHANNEL` | 空 | PushPlus 渠道 |
| `WECOM_TOUSER` | `@all` | 企业微信接收人 |
| `WXPUSHER_UIDS` | 空 | WxPusher UID 列表（逗号分隔） |
| `WXPUSHER_TOPIC_IDS` | 空 | WxPusher Topic ID 列表 |
| `BARK_SERVER_URL` | `https://api.day.app` | Bark 服务器地址 |
| `BARK_GROUP` | `洛克王国` | Bark 消息分组 |
| `NTFY_BASE_URL` | `https://ntfy.sh` | ntfy 服务器地址 |
| `NTFY_PRIORITY` | `default` | ntfy 优先级 |
| `NTFY_TAGS` | 空 | ntfy 标签 |
| `GOTIFY_BASE_URL` | 空 | Gotify 服务器地址 |
| `GOTIFY_PRIORITY` | `5` | Gotify 优先级 |

## 项目结构

```
cf-workers/
├── _worker.js                 # 控制台粘贴部署文件
├── wrangler.toml              # Wrangler 项目部署和本地调试配置
├── package.json               # 脚本和依赖
├── tsconfig.json              # TypeScript 配置（strict, ES2022）
├── .gitignore                 # 忽略 node_modules、.wrangler、.dev.vars、dist
├── .dev.vars.example          # 本地调试 secrets 模板
├── scripts/
│   └── write-worker-bundle.mjs # 从 Wrangler bundle 生成 _worker.js
├── test/
│   └── worker.test.ts         # Worker 单元测试
├── README.md                  # 本文档
└── src/
    ├── index.ts               # 入口：scheduled（cron）+ fetch（HTTP）handler
    ├── types.ts               # 所有 TypeScript 接口定义
    ├── config.ts              # 环境变量 → Config 对象构建
    ├── rocom.ts               # API 客户端 + 时间工具 + Markdown 构建
    ├── push.ts                # 10 个推送通道实现 + 投递引擎
    └── provider-specs.ts      # 通道字段规格定义（required/secret/default）
```

源码映射：

| Python 文件 | TypeScript 文件 | 内容 |
|---|---|---|
| `app.py` | `index.ts` | 流程编排 |
| `config.py` | `config.ts` | 环境变量映射 |
| `rocom.py` | `rocom.ts` | API 客户端 |
| `time_utils.py` | `rocom.ts` | 时间工具（合并） |
| `push.py` | `push.ts` | 10 个通道 + 投递引擎 |
| `provider_specs.py` | `provider-specs.ts` | 通道规格 |

## 本地调试与维护

部署不要求本地环境；以下命令只用于调试、测试、项目部署和重新生成 `_worker.js`。

```bash
cd cf-workers
npm ci

# 本地调试 secrets
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 填入 ROCOM_API_KEY 和至少一个推送通道

# 本地启动 Worker
npm run dev
# http://localhost:8787/health
# http://localhost:8787/trigger

# 测试与检查
npm test
npx tsc --noEmit
npm run dry-run

# 重新生成控制台粘贴文件，并检查 _worker.js 是否已提交
npm run check:worker
```

提交 PR 前建议运行：

```bash
npm ci
npm test
npx tsc --noEmit
npm run check:worker
```

## 从其他部署方式迁移

### 从 GitHub Actions 迁移

GitHub Actions 的定时任务可能延迟或被暂停，CF Workers 更稳定。

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [_worker.js](_worker.js)。
2. 将 GitHub Actions Secrets 中的值迁移到 Worker 的 Variables and Secrets。
3. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`。
4. 手动访问 `/trigger` 验证。
5. 确认正常后，删除或停用 `.github/workflows/scheduled-push.yml`。

### 从 Docker 版迁移

| Docker 环境变量 | CF Workers 配置 |
|---|---|
| `ROCOM_API_KEY` | Secret |
| `SERVERCHAN_SENDKEY` | Secret |
| `DELIVERY_MODE` | Variable |
| `NOTIFY_EMPTY` | Variable |
| `HTTP_TIMEOUT` | Variable |
| 其他通道 Key | Secret |
| 其他通道可选参数 | Variable |

不需要迁移 `APP_MODE`、`WEB_PORT`、`CONSOLE_*`、`SCHEDULE_TIMES`、`RUN_ON_START`，这些只属于 Docker 版。

## 外部监控集成

任何支持 HTTP 健康检查的服务都可以监控 `/health`：

- [UptimeRobot](https://uptimerobot.com/)
- [Better Uptime](https://betteruptime.com/)
- [Freshping](https://www.freshworks.com/website-monitoring/)
- [Hetrix Tools](https://hetrixtools.com/)

## 费用说明

本 Worker 默认每天 4 次触发，每月约 120 次调度，请求量很低，通常适合 Cloudflare Workers 免费计划。实际额度、Cron Triggers 数量、子请求和 CPU 限制请以 Cloudflare Workers 官方文档为准。

## 常见问题

### 应该选控制台粘贴还是 Wrangler 项目部署？

普通使用者选控制台粘贴，步骤少，也不需要 Node.js。维护者或需要 CI、源码变更、自动化发布的人选 Wrangler 项目部署。

### `_worker.js` 是手写的吗？

不是。源码在 `src/*.ts`，`_worker.js` 由 `npm run build:worker` 生成。改源码后需要重新生成并提交 `_worker.js`。

### 如何添加新的推送通道？

控制台粘贴部署：在 Worker 控制台添加对应 Secret/Variable。Wrangler 项目部署：Secret 用 `npx wrangler secret put <NAME>`，非敏感变量写入 `wrangler.toml` 后执行 `npm run deploy`。

### 如何修改定时时间？

控制台粘贴部署：在 Dashboard → Worker → Triggers → Cron Triggers 修改。Wrangler 项目部署：修改 `wrangler.toml` 的 `[triggers]` 后执行 `npm run deploy`。

### 如何查看执行日志？

在 Cloudflare Dashboard → Workers → 你的 Worker → Logs 查看。Wrangler 项目部署也可以使用：

```bash
npm run tail
```

### 为什么没有收到推送？

1. 检查 `ROCOM_API_KEY` 是否已配置。
2. 确认至少一个推送通道的必需字段完整。
3. 手动触发 `curl <worker-url>/trigger`。
4. 如果配置了 `TRIGGER_TOKEN`，请求需带 `?token=`、`X-Trigger-Token` 或 `Authorization: Bearer`。
5. 查看 Worker Logs 中的错误信息。

### 如何更新到最新版本？

控制台粘贴部署：复制新版 [_worker.js](_worker.js) 全量内容，替换 Worker 编辑器中的代码并保存部署。

Wrangler 项目部署：

```bash
cd cf-workers
git pull
npm ci
npm run deploy
```

### Worker 名称可以改吗？

可以。控制台粘贴部署时在 Dashboard 创建或重命名 Worker；Wrangler 项目部署时修改 `wrangler.toml` 中的 `name` 后重新部署。

## 许可

本项目使用 [MIT License](../LICENSE)。
