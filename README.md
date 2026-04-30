# 洛克王国世界远行商人推送控制台

[![Docker Image](https://img.shields.io/badge/docker-linxi5013%2Froco--push--console-2496ed?logo=docker&logoColor=white)](https://hub.docker.com/r/linxi5013/roco-push-console)
[![CI](https://github.com/adrian803/roco-push-console/actions/workflows/ci.yml/badge.svg)](https://github.com/adrian803/roco-push-console/actions/workflows/ci.yml)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare%20Workers-_worker.js-F6821F?logo=cloudflare&logoColor=white)](cf-workers/_worker.js)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

监控《洛克王国世界》远行商人刷新状态的推送服务。提供 **Docker 部署**（含 Web 控制台）、**GitHub Actions 定时推送**和 **Cloudflare Workers 免费托管**三种方式，将刷新结果推送到 10 种主流推送通道。

推送内容以文字和 Markdown 为主，不内置图片渲染和图片推送逻辑。

## 目录

- [截图](#截图)
- [功能特性](#功能特性)
- [部署方式选择](#部署方式选择)
- [快速开始](#快速开始)
  - [方式一：只填 Key 自动托管](#方式一只填-key-自动托管)
  - [方式二：Docker Hub 镜像 + Web 控制台](#方式二docker-hub-镜像--web-控制台)
  - [方式三：docker compose](#方式三docker-compose)
  - [方式四：Cloudflare Workers](#方式四cloudflare-workers)
- [首次配置](#首次配置)
- [推送通道](#推送通道)
- [发送策略](#发送策略)
- [环境变量](#环境变量)
- [常用命令](#常用命令)
- [本地开发](#本地开发)
- [GitHub Actions 定时推送](#github-actions-定时推送)
- [Cloudflare Workers 详细说明](#cloudflare-workers-详细说明)
- [常见问题](#常见问题)
- [安全提醒](#安全提醒)
- [来源与鸣谢](#来源与鸣谢)
- [贡献](#贡献)
- [许可](#许可)

## 截图

| 登录页 | 控制台 |
|:------:|:------:|
| <img src="docs/images/login.png" alt="登录页" width="380"> | <img src="docs/images/console.png" alt="控制台" width="380"> |

Server 酱推送效果：

<img src="docs/images/serverchan-push.png" alt="Server 酱推送效果" width="320">

## 功能特性

**核心能力**

- 10 种推送通道：Server 酱、PushPlus、企业微信、WxPusher、Bark、钉钉、飞书、ntfy、Gotify
- 默认定时 `08:05,12:05,16:05,20:05` 推送（远行商人刷新后 5 分钟，给数据源留同步时间）
- 支持多通道同时发送、单通道发送、主备失败切换
- 三种部署方式：Docker / GitHub Actions / Cloudflare Workers

**Web 控制台**（Docker 版）

- 页面管理配置，无需反复改环境变量
- 单通道测试和按当前策略测试
- 敏感字段保存后不回显，页面显示"已配置，留空不改"
- 推送异常和 HTTP 错误脱敏，避免 token 出现在控制台和 Docker 日志

**可靠性**

- 配置持久化到 `./data/config.json`（Docker 版）
- 读取损坏配置时自动备份原文件，不会覆盖旧配置
- 容器启动时自动修正 `/data` 目录权限，适配 WSL / bind mount

## 部署方式选择

| | Docker | GitHub Actions | Cloudflare Workers |
|---|:---:|:---:|:---:|
| **需要服务器** | 是 | 否 | 否 |
| **Web 控制台** | 有 | 无 | 无 |
| **费用** | 服务器费用 | 免费 | 免费 |
| **定时精确度** | 精确到秒 | 延迟几分钟 | 延迟 1-2 分钟 |
| **长期稳定性** | 高 | 中（可能被暂停） | 高 |
| **配置方式** | 页面 / 环境变量 | GitHub Secrets | Worker 控制台变量 / Wrangler |
| **适合场景** | 长期运行、需要 Web 管理 | 偶尔使用、不想运维 | 免费长期托管 |

**推荐：**

- 需要 Web 控制台 → **Docker**
- 想要免费且稳定 → **Cloudflare Workers**
- 已有 GitHub 仓库、偶尔用用 → **GitHub Actions**

## 快速开始

### 方式一：只填 Key 自动托管

适合不想使用 Web UI、只想长期托管的场景。默认在远行商人刷新后 5 分钟推送。

Server 酱示例：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=你的接口Key \
  -e SERVERCHAN_SENDKEY=你的Server酱SendKey \
  linxi5013/roco-push-console:latest
```

PushPlus 示例：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=你的接口Key \
  -e PUSHPLUS_TOKEN=你的PushPlusToken \
  linxi5013/roco-push-console:latest
```

这种模式不会监听 `19892`，不需要配置 `CONSOLE_USERNAME`、`CONSOLE_PASSWORD`、`WEB_PORT`。

### 方式二：Docker Hub 镜像 + Web 控制台

想通过页面配置和测试通道时，显式设置 `APP_MODE=web`：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -p 19892:19892 \
  -v ./data:/data \
  -e APP_MODE=web \
  -e CONSOLE_USERNAME=admin \
  -e CONSOLE_PASSWORD=你的控制台密码 \
  linxi5013/roco-push-console:latest
```

启动后打开 `http://服务器IP:19892`。

### 方式三：docker compose

```bash
git clone https://github.com/adrian803/roco-push-console.git
cd roco-push-console
cp .env.example .env
```

编辑 `.env`，填入必需 Key：

```env
ROCOM_API_KEY=你的接口Key
SERVERCHAN_SENDKEY=你的Server酱SendKey
```

启动：

```bash
docker compose up -d
```

如果想使用 Web 控制台，在 `.env` 中额外设置：

```env
APP_MODE=web
CONSOLE_USERNAME=admin
CONSOLE_PASSWORD=你的控制台密码
WEB_PORT=19892
```

**`APP_MODE` 说明：**

| 值 | 行为 |
|---|---|
| `auto`（默认） | 配置齐时只启动调度器；缺配置时启动 Web 控制台 |
| `web` | 强制启动 Web 控制台 |
| `scheduler` | 强制无控制台运行 |
| `once` | 执行一次检查后退出 |

### 方式四：Cloudflare Workers

不需要服务器，使用 Cloudflare 免费 Cron Triggers 定时执行，全球边缘节点运行。

**控制台粘贴部署（推荐普通用户）：**

1. 打开 Cloudflare Dashboard → Workers & Pages → Create Worker
2. 进入 Worker 编辑器，删除默认代码
3. 将 [cf-workers/_worker.js](cf-workers/_worker.js) 的完整内容粘贴进去并保存部署
4. 在 Settings → Variables and Secrets 中添加 `ROCOM_API_KEY` 和至少一个推送通道 secret
5. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`

部署后自动按 cron 调度运行（北京时间 08:05 / 12:05 / 16:05 / 20:05）。也可以手动触发：

```bash
# 开放模式
curl https://roco-push-worker.<子域>.workers.dev/trigger

# 配置 TRIGGER_TOKEN 后，任选一种方式传入 token
curl "https://roco-push-worker.<子域>.workers.dev/trigger?token=你的token"
curl -H "X-Trigger-Token: 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
curl -H "Authorization: Bearer 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
```

**配置发送策略（可选）：**

在 Worker 控制台的 Settings → Variables and Secrets 中添加普通变量：

| 变量 | 示例 |
|------|------|
| `DELIVERY_MODE` | `failover` |
| `SELECTED_PROVIDER` | `serverchan-default` |
| `FAILOVER_ORDER` | `pushplus-env,serverchan-default` |

可用通道 ID：`serverchan-default`、`pushplus-env`、`wecomchan-env`、`wecom-bot-env`、`wxpusher-env`、`bark-env`、`dingtalk-env`、`feishu-env`、`ntfy-env`、`gotify-env`。

**Wrangler 项目部署（适合维护者）：**

```bash
cd cf-workers
npm ci
npx wrangler login
npx wrangler secret put ROCOM_API_KEY
npx wrangler secret put SERVERCHAN_SENDKEY  # 至少一个推送通道
npm run deploy
```

Wrangler 部署会使用 `cf-workers/wrangler.toml` 中的 Cron 和非敏感变量；如果采用这种方式，建议后续也用项目配置管理 Worker，避免和控制台手动配置互相覆盖。

详细说明见 [cf-workers/README.md](cf-workers/README.md)。

## 首次配置

### Docker 版（Web 控制台）

进入控制台后按此顺序操作：

1. **基础配置** — 填写 `ROCOM_API_KEY`
2. **数据接口** — 通常保持默认即可
3. **北京时间定时** — 默认 `08:05,12:05,16:05,20:05`
4. **通道配置** — 添加推送通道，填写 token / webhook
5. 点击单通道 **"测试"**，确认收到消息
6. 选择发送策略并 **保存配置**
7. 点击 **"立即执行"** 做一次手动检查

配置保存到 `./data/config.json`。

### CF Workers 版（环境变量）

普通部署在 Cloudflare Worker 控制台的 Settings → Variables and Secrets 中配置。使用 Wrangler 项目部署时，secrets 通过 `wrangler secret put` 配置，非敏感变量放在 `cf-workers/wrangler.toml`。必需配置 `ROCOM_API_KEY` 和至少一个推送通道 secret；可选配置 `TRIGGER_TOKEN` 保护 `/trigger` 端点。详见 [cf-workers/README.md](cf-workers/README.md#环境变量参考)。

## 推送通道

10 种推送通道，Docker 版和 CF Workers 版完全一致：

| 通道 | 必填配置 | 说明 |
|------|---------|------|
| Server 酱 | SendKey | 推送到微信 |
| PushPlus | Token | 支持 topic、channel，默认 Markdown |
| Wecom 酱 / 企业微信应用 | CorpID、Secret、AgentID、接收人 | 自动获取并缓存 access token |
| 企业微信群机器人 | Webhook 或 Key | 发送 Markdown 消息 |
| WxPusher | AppToken | 支持 UID 列表或 Topic ID 列表 |
| Bark | Server URL、Device Key | 推送到 iOS Bark |
| 钉钉群机器人 | Webhook | 可选 secret 加签 |
| 飞书群机器人 | Webhook | 可选 secret 加签 |
| ntfy | Base URL、Topic | 可选 bearer token、priority、tags |
| Gotify | Base URL、App Token | 可配置 priority |

**Docker 版通道卡片说明：**

- **名称**：给自己看的显示名，比如"我的 Server 酱"
- **启用**：关闭后该通道不参与发送
- 服务商参数：如 Server 酱的 `SendKey`、PushPlus 的 `Token`

程序内部会为每个通道生成稳定 ID，用于配置保存和主备切换，不需要手动填写。使用"主备切换"策略时，按页面卡片顺序尝试，越靠上越先尝试，可用"上移""下移"调整优先级。

## 发送策略

通过 `DELIVERY_MODE` 控制（Docker 版在 Web 控制台选择，CF Workers 版在 Worker 控制台变量或 `wrangler.toml` 设置）：

| 策略 | 值 | 行为 |
|------|---|------|
| 所有启用通道同时发送 | `all` | 向全部启用通道发送，至少一个成功即认为送达 |
| 只发送选中通道 | `single` | 只向选中的通道发送 |
| 主备切换，成功即停 | `failover` | 按通道列表顺序尝试，第一个成功后停止 |

CF Workers 版可通过 `SELECTED_PROVIDER` 指定 `single` 的通道，通过 `FAILOVER_ORDER` 指定 `failover` 的逗号分隔顺序。可用通道 ID 见 [cf-workers/README.md](cf-workers/README.md#发送策略)。

## 环境变量

`.env` 里的 `ROCOM_API_KEY`、推送通道 Key 和定时时间会作为默认配置读取。使用 Web 控制台保存过配置后，会优先读取 `./data/config.json`；自动托管或无控制台模式时，可以只维护 `.env` 或 `docker run -e` 参数。

**基础变量：**

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `APP_MODE` | `auto` | 运行模式：`auto` / `web` / `scheduler` / `once` |
| `WEB_PORT` | `19892` | 宿主机访问端口 |
| `CONSOLE_USERNAME` | `admin` | 控制台用户名 |
| `CONSOLE_PASSWORD` | 空 | 控制台密码；为空时不启用认证 |
| `CONSOLE_SESSION_TTL` | `86400` | 登录态有效期（秒） |
| `CONSOLE_SESSION_SECRET` | 空 | Cookie 签名密钥；默认使用控制台密码 |
| `ROCOM_API_KEY` | 空 | 数据源接口 Key |
| `ROCOM_API_URL` | 空 | 自定义数据接口，空则使用内置默认值 |
| `DELIVERY_MODE` | `all` | 发送策略：`all` / `single` / `failover` |
| `SCHEDULE_TIMES` | `08:05,12:05,16:05,20:05` | 定时推送时间 |
| `RUN_ON_START` | `false` | 容器启动后是否立即执行一次 |
| `NOTIFY_EMPTY` | `false` | 没有商品时是否也推送 |
| `HTTP_TIMEOUT` | `30` | 请求超时秒数 |

**无控制台通道变量：**

没有 `./data/config.json` 且配置文件未写入 `providers` 时，程序会根据环境变量自动创建推送通道。只填你要用的那一组即可。

| 通道 | 最少需要 | 可选 |
|------|---------|------|
| Server 酱 | `SERVERCHAN_SENDKEY` | — |
| PushPlus | `PUSHPLUS_TOKEN` | `PUSHPLUS_TOPIC`、`PUSHPLUS_CHANNEL` |
| Wecom 酱 / 企业微信应用 | `WECOM_CORPID`、`WECOM_SECRET`、`WECOM_AGENTID` | `WECOM_TOUSER`（默认 `@all`） |
| 企业微信群机器人 | `WECOM_BOT_WEBHOOK` 或 `WECOM_BOT_KEY` | — |
| WxPusher | `WXPUSHER_APP_TOKEN` | `WXPUSHER_UIDS`、`WXPUSHER_TOPIC_IDS` |
| Bark | `BARK_DEVICE_KEY` | `BARK_SERVER_URL`、`BARK_GROUP` |
| 钉钉群机器人 | `DINGTALK_WEBHOOK` | `DINGTALK_SECRET` |
| 飞书群机器人 | `FEISHU_WEBHOOK` | `FEISHU_SECRET` |
| ntfy | `NTFY_TOPIC` | `NTFY_BASE_URL`、`NTFY_TOKEN`、`NTFY_PRIORITY`、`NTFY_TAGS` |
| Gotify | `GOTIFY_BASE_URL`、`GOTIFY_APP_TOKEN` | `GOTIFY_PRIORITY` |

> CF Workers 版的环境变量略有不同，详见 [cf-workers/README.md](cf-workers/README.md#环境变量参考)。

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 重启
docker compose restart

# 升级到最新镜像
docker compose pull && docker compose up -d

# 停止并移除容器
docker compose down

# 备份配置
cp ./data/config.json ./config.backup.json
```

## 本地开发

### Docker 版（Python）

```bash
# 环境准备
uv sync --frozen

# 启动 Web 控制台
uv run python -m roco_push_console.web

# 启动自动模式
uv run python -m roco_push_console.launcher

# 一次性执行检查
uv run python main.py

# 运行测试
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet

# 构建镜像
docker build -t roco-push-console:latest .
```

### CF Workers 版（本地调试）

控制台粘贴部署不需要本地环境；以下命令用于调试、测试、Wrangler 项目部署，以及从 TypeScript 源码重新生成可粘贴的 `_worker.js`。

```bash
cd cf-workers
npm install

# 复制 secrets 模板
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 填入你的 secrets

# 本地调试
npm run dev
# 访问 http://localhost:8787/health
# 手动触发 http://localhost:8787/trigger

# 测试、类型检查和生成粘贴文件
npm test
npx tsc --noEmit
npm run build:worker

# 可选：Wrangler 项目部署
npm run deploy
```

## GitHub Actions 定时推送

不需要部署服务器，直接用 GitHub Actions 免费定时运行推送检查。默认 cron 对应北京时间：

| 本地时间 | UTC cron |
|:--------:|:--------:|
| 08:05 | `5 0 * * *` |
| 12:05 | `5 4 * * *` |
| 16:05 | `5 8 * * *` |
| 20:05 | `5 12 * * *` |

**配置步骤：**

1. 仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 添加以下 Secret（至少选一个推送通道）：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 SendKey（或替换为其他通道） |

可选添加 Repository Variable：`PUSHPLUS_TOKEN`、`DELIVERY_MODE`、`NOTIFY_EMPTY`、`HTTP_TIMEOUT` 等。

> **注意：** GitHub Actions 定时任务不是严格实时，可能延迟几分钟；只在默认分支生效，仓库长期无活动可能被暂停。如果需要更稳定的免费方案，推荐使用 [Cloudflare Workers](#方式四cloudflare-workers)。

**其他 Actions 工作流：**

- `ci.yml` — PR 和 push 时运行测试 + 编译检查
- `docker-publish.yml` — 自动构建并发布多架构镜像（`amd64` / `arm64`）到 Docker Hub

## Cloudflare Workers 详细说明

CF Workers 版是本项目的第三种部署方式，将核心推送逻辑打包为单文件 [cf-workers/_worker.js](cf-workers/_worker.js)，使用 Cloudflare Cron Triggers 定时执行。

**架构：**

```
Cron Trigger → fetchMerchantData → processMerchantData → sendDelivery
(每天4次)       (获取数据)           (过滤+构建消息)       (推送到10种通道)
```

**文件结构：**

```
cf-workers/
├── _worker.js             # 控制台部署时粘贴的单文件 Worker
├── wrangler.toml          # Wrangler 项目部署 / 本地调试配置
├── package.json           # 依赖 + 项目元数据
├── tsconfig.json          # TypeScript 严格模式配置
├── .dev.vars.example      # 本地调试 secrets 模板
└── src/
    ├── index.ts           # 入口：scheduled + fetch handler
    ├── types.ts           # 接口定义
    ├── config.ts          # 环境变量 → Config
    ├── rocom.ts           # API 客户端 + 时间工具
    ├── push.ts            # 10 个推送通道 + 投递引擎
    └── provider-specs.ts  # 通道规格定义
```

**HTTP 端点：**

| 路径 | 说明 |
|------|------|
| `/health` | 健康检查，返回 `{ ok: true, timestamp: "..." }` |
| `/trigger` | 手动触发一次推送，返回执行结果 |

`/trigger` 默认保持开放；配置 `TRIGGER_TOKEN` secret 后，触发请求必须提供匹配的 token。支持三种传入方式：

- 查询参数：`?token=你的token`
- 请求头：`X-Trigger-Token: 你的token`
- Bearer 认证：`Authorization: Bearer 你的token`

Cron Trigger 和 `/health` 不受 `TRIGGER_TOKEN` 影响。

**本地调试与测试：**

```bash
cd cf-workers
cp .dev.vars.example .dev.vars   # 填入 secrets
npm test                          # 运行单元测试
npx tsc --noEmit                  # 类型检查
npm run build:worker              # 重新生成 _worker.js
npm run dev                       # 可选，本地启动 Worker 调试
```

**费用：** 默认每天 4 次触发 = 每月约 120 次，请求量很低，通常适合 Cloudflare Workers 免费计划。具体额度以 [Cloudflare Workers Limits](https://developers.cloudflare.com/workers/platform/limits/) 为准。

完整说明见 [cf-workers/README.md](cf-workers/README.md)。

## 常见问题

<details>
<summary><b>如何获取 ROCOM_API_KEY？</b></summary>

请按 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 项目或相关社区的规则获取。本项目不提供、不分发 API Key。

</details>

<details>
<summary><b>三种部署方式怎么选？</b></summary>

- 需要 Web 控制台管理配置 → **Docker**
- 想免费且稳定运行 → **Cloudflare Workers**
- 已有 GitHub 仓库、偶尔用 → **GitHub Actions**

三种方式的推送逻辑完全一致，区别在于配置方式和运维成本。

</details>

<details>
<summary><b>为什么打开控制台不需要密码？</b></summary>

`CONSOLE_PASSWORD` 为空时会关闭认证。部署到局域网或公网前请设置密码，或使用 `APP_MODE=auto` 填齐 Key 让服务进入无控制台托管模式。

</details>

<details>
<summary><b>为什么没有启动 Web 控制台？</b></summary>

默认 `APP_MODE=auto` 会在配置齐全时只启动调度器，不监听 `19892`。设置 `APP_MODE=web` 后重建容器即可强制启动。

</details>

<details>
<summary><b>为什么提示缺少 ROCOM_API_KEY？</b></summary>

本项目不提供 API Key。请按 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 项目或相关社区的规则获取 `ROCOM_API_KEY`，再填入控制台或 `.env`。

</details>

<details>
<summary><b>为什么修改 .env 后页面没变？</b></summary>

控制台保存过配置后，会优先读取 `./data/config.json`。后续更推荐在 Web 控制台修改；如要完全使用 `.env` 默认值，需先备份并移走 `config.json`。

</details>

<details>
<summary><b>为什么收不到推送？</b></summary>

**Docker 版：** 先在"通道配置"里点击单通道"测试"。如果测试失败，检查 token / webhook 是否正确、服务商是否限流、服务器是否能访问对应推送服务。

**CF Workers 版：** 手动触发 `curl <worker-url>/trigger`，查看返回结果。若配置了 `TRIGGER_TOKEN`，使用 `curl '<worker-url>/trigger?token=你的token'`。执行日志优先在 Cloudflare Dashboard → Workers → 你的 Worker → Logs 查看；Wrangler 项目部署也可以在 `cf-workers` 目录运行 `npm run tail`。

**GitHub Actions 版：** 查看 Actions 运行日志，确认 secrets 是否配置正确。

</details>

<details>
<summary><b>配置文件损坏怎么办？</b></summary>

程序读取失败时会把损坏文件备份为 `config.json.invalid-时间戳.bak`，并在控制台状态区显示提示。

</details>

<details>
<summary><b>保存配置提示 Permission denied？</b></summary>

旧容器在 WSL + bind mount 场景下可能出现权限问题。执行：

```bash
docker exec -u root roco-push-console chown -R app:app /data
```

然后刷新再保存。长期建议更新镜像并重建容器：

```bash
docker compose pull && docker compose up -d --force-recreate
```

</details>

<details>
<summary><b>GitHub Actions 定时不准怎么办？</b></summary>

GitHub Actions 的 cron 不保证精确执行，可能延迟几分钟，仓库长期不活跃还会被暂停。推荐迁移到 [Cloudflare Workers](#方式四cloudflare-workers)，同样免费但更稳定。

</details>

<details>
<summary><b>如何从 GitHub Actions 迁移到 CF Workers？</b></summary>

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [cf-workers/_worker.js](cf-workers/_worker.js)
2. 将 GitHub Secrets 中的值迁移到 Worker 的 Variables and Secrets
3. 删除仓库中的 `.github/workflows/scheduled-push.yml`
4. CI 和 Docker Publish workflows 保留不变

</details>

## 安全提醒

### Docker 版

默认 `APP_MODE=auto`：配置齐时容器只启动调度器，不启动 Web 控制台；缺少配置时才启动控制台方便首次配置。

如果使用 `APP_MODE=web`，或因缺少 Key 进入控制台模式，控制台监听 `0.0.0.0` 并发布到宿主机 `19892` 端口。`CONSOLE_PASSWORD` 为空时关闭认证。

**公开部署前请务必：**

- 在 `.env` 设置强密码：`CONSOLE_PASSWORD=你的密码`
- 只在可信网络开放 `19892`，或用防火墙 / 反向代理限制访问
- 本机访问改为 `127.0.0.1:${WEB_PORT:-19892}:19892`
- 不要提交 `./data/config.json`（含明文 token 和 Key）

### CF Workers 版

Secrets 通过 Cloudflare Worker 控制台加密存储，不会出现在代码或日志中。`/trigger` 端点默认开放；公开分享 Worker URL 前建议配置 `TRIGGER_TOKEN`，让手动触发必须带 token。

## 来源与鸣谢

远行商人数据来自 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的接口。本仓库只负责调用接口并展示、推送结果，不内置、不分发 `ROCOM_API_KEY`，也不代为申请 Key。请按数据源项目或相关社区的规则获取 Key。

本项目不会绕过数据源服务端限制，接口调用频率以数据源后端实际限制为准。请合理设置定时任务，避免给数据源服务带来不必要的压力。

已询问过数据源项目提供方，本项目只是调用 Entropy-Increase-Team 的接口，标注数据来源即可。若需直接使用或改造其代码，会按其 AGPL-3.0 协议要求处理。

## 贡献

欢迎提交 issue 和 pull request。适合贡献的方向：

- 新推送通道
- 控制台交互优化
- 部署文档
- 测试用例

提交 PR 前请运行：

```bash
# Docker 版
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet

# CF Workers 版
cd cf-workers
npm ci
npm test
npx tsc --noEmit
npm run check:worker
```

## 路线图

- 支持更多推送平台
- 增加更完整的端到端测试
- ~~Cloudflare Workers Cron 适配器~~ ✅ 已完成

## 免责声明

本项目是个人学习和自用工具，和游戏官方、WeGame、各推送平台均无从属关系。项目只保存使用者自行填写的接口 Key 和推送 token，不提供、不出售、不共享任何第三方 API Key。请遵守相关服务条款，不要滥用接口或推送能力。

## 许可

本项目使用 [MIT License](LICENSE)。
