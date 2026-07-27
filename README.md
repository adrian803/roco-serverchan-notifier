# 洛克王国世界远行商人推送控制台（飞书图片增强版）

[![Docker Image](https://img.shields.io/badge/ghcr.io-boater--man%2Froco--serverchan--notifier-2496ed?logo=docker&logoColor=white)](https://github.com/boater-man/roco-serverchan-notifier/pkgs/container/roco-serverchan-notifier)
[![CI](https://github.com/boater-man/roco-serverchan-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/boater-man/roco-serverchan-notifier/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Fork 自 [linxi5013/roco-serverchan-notifier](https://github.com/linxi5013/roco-serverchan-notifier)**，在原版基础上增加了**飞书通道图片直接推送**功能。

监控《洛克王国世界》远行商人刷新状态，支持 **12 种推送通道**，本 Fork 重点增强了飞书通道的图片推送能力。

## ✨ 本 Fork 改进：飞书图片直接推送

### 原版问题

原版飞书通道仅支持文字推送，图片渲染后只能保存到本地或以文字描述替代，无法在飞书群内直接展示商品卡片图片。

### 改进方案

本 Fork 通过飞书 Open API 实现图片直接推送到群聊：

```
定时任务触发 (08:05 / 12:05 / 16:05 / 20:05)
    ↓
调用洛克王国 API 获取远行商人信息
    ↓
Pillow 渲染商品卡片图片
    ↓
飞书 Open API 上传图片 → 获取 image_key
    ↓
Webhook 发送图片消息到飞书群
    ↓
(降级) 上传失败时回退到卡片文本消息
```

**核心改动：**
- 通过 `FEISHU_APP_ID` + `FEISHU_APP_SECRET` 获取 `tenant_access_token`（带缓存）
- 调用 `im/v1/images` API 上传图片，获取 `image_key`
- 通过 Webhook 以 `msg_type: "image"` 直接发送图片
- 图片同时保存到 `/data/images/` 供宿主机脚本备用

## 📦 镜像

镜像已发布到 GitHub Container Registry：

```
ghcr.io/boater-man/roco-serverchan-notifier:latest
ghcr.io/boater-man/roco-serverchan-notifier:feishu-image
```

## 🚀 部署

### Docker（飞书图片模式）

```bash
docker run -d \
  --name roco-serverchan-notifier \
  --restart unless-stopped \
  -p 19892:19892 \
  -v ./data:/data \
  -e APP_MODE=web \
  -e CONSOLE_USERNAME=admin \
  -e CONSOLE_PASSWORD=你的控制台密码 \
  -e ROCOM_API_KEY=你的接口Key \
  -e FEISHU_WEBHOOK=你的飞书Webhook地址 \
  -e FEISHU_APP_ID=你的飞书AppID \
  -e FEISHU_APP_SECRET=你的飞书AppSecret \
  -e RENDER_IMAGE=true \
  -e SCHEDULE_TIMES=08:05,12:05,16:05,20:05 \
  ghcr.io/boater-man/roco-serverchan-notifier:latest
```

### Docker Compose

```yaml
services:
  roco-serverchan-notifier:
    image: ghcr.io/boater-man/roco-serverchan-notifier:latest
    container_name: roco-serverchan-notifier
    restart: unless-stopped
    ports:
      - "19892:19892"
    volumes:
      - ./data:/data
    environment:
      TZ: Asia/Shanghai
      APP_MODE: web
      WEB_HOST: 0.0.0.0
      WEB_PORT: 19892
      CONSOLE_USERNAME: admin
      CONSOLE_PASSWORD: ${CONSOLE_PASSWORD:-}
      ROCOM_API_KEY: ${ROCOM_API_KEY:-}
      # 飞书通道配置
      FEISHU_WEBHOOK: ${FEISHU_WEBHOOK:-}
      FEISHU_APP_ID: ${FEISHU_APP_ID:-}
      FEISHU_APP_SECRET: ${FEISHU_APP_SECRET:-}
      # 启用图片渲染
      RENDER_IMAGE: "true"
      # 定时推送时间
      SCHEDULE_TIMES: "08:05,12:05,16:05,20:05"
```

`.env` 文件示例：

```env
CONSOLE_PASSWORD=your_password
ROCOM_API_KEY=your_rocom_key
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxx
```

## ⚙️ 飞书配置说明

要使用图片推送功能，需要在飞书开放平台创建应用并获取凭证：

1. 访问 [飞书开放平台](https://open.feishu.cn/) 创建企业自建应用
2. 获取 `App ID` 和 `App Secret`
3. 在应用权限中添加 `im:resource`（上传图片）权限
4. 创建 Webhook 机器人并获取 Webhook 地址
5. 将以上信息填入环境变量

**必需环境变量：**

| 变量 | 说明 |
|------|------|
| `FEISHU_WEBHOOK` | 飞书 Webhook 地址 |
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `RENDER_IMAGE` | 设为 `true` 启用图片渲染 |

## 📡 支持的推送通道

| 通道 | 环境变量 | 图片支持 |
|------|----------|----------|
| 飞书 | `FEISHU_WEBHOOK` + `FEISHU_APP_ID` + `FEISHU_APP_SECRET` | ✅ 直接推送 |
| Server 酱 | `SERVERCHAN_SENDKEY` | ❌ 纯文字 |
| PushPlus | `PUSHPLUS_TOKEN` | ❌ 纯文字 |
| Telegram | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | ❌ 纯文字 |
| Discord | `DISCORD_WEBHOOK` | ❌ 纯文字 |
| 企业微信 | `WECOM_CORPID` + `WECOM_SECRET` + `WECOM_AGENTID` | ❌ 纯文字 |
| 钉钉 | `DINGTALK_WEBHOOK` + `DINGTALK_SECRET` | ❌ 纯文字 |
| Bark | `BARK_DEVICE_KEY` | ❌ 纯文字 |
| ntfy | `NTFY_TOPIC` | ❌ 纯文字 |
| Gotify | `GOTIFY_APP_TOKEN` | ❌ 纯文字 |
| WxPusher | `WXPUSHER_APP_TOKEN` | ❌ 纯文字 |

## 🔧 与原版差异

| 功能 | 原版 | 本 Fork |
|------|------|---------|
| 飞书推送 | 纯文字 | **图片 + 卡片** |
| 图片渲染 | 无 | Pillow 渲染商品卡片 |
| 图片上传 | 无 | 飞书 Open API |
| 降级方案 | 无 | 图片失败回退卡片 |

## 📖 原版文档

完整功能说明、环境变量参考、其他部署方式（GitHub Actions、Cloudflare Workers）请参考原版文档：

- [原版 README](https://github.com/linxi5013/roco-serverchan-notifier/blob/main/README.md)
- [环境变量参考](docs/reference/environment-variables.md)
- [推送通道与发送策略](docs/reference/providers-and-delivery.md)
- [Cloudflare Workers 部署](docs/deployment/cloudflare-workers.md)
- [GitHub Actions 部署](docs/deployment/github-actions.md)

## 🙏 致谢

- 原版项目：[linxi5013/roco-serverchan-notifier](https://github.com/linxi5013/roco-serverchan-notifier)
- 数据源：[Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的《洛克王国世界》接口

## 📄 许可

本项目使用 [MIT License](LICENSE)。
