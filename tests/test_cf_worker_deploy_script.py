from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudflareDeployScriptDocsTests(unittest.TestCase):
    def test_deploy_script_contains_expected_safety_and_deploy_steps(self):
        script = ROOT / "scripts" / "deploy-cf-worker.ps1"
        content = script.read_text(encoding="utf-8")

        self.assertIn("NonInteractive", content)
        self.assertIn("DeployMode", content)
        self.assertIn("Source", content)
        self.assertIn("WorkerJs", content)
        self.assertIn("Read-YesNo", content)
        self.assertIn("请选择部署方式", content)
        self.assertIn("npx 编译/项目部署", content)
        self.assertIn("直接部署项目内 _worker.js", content)
        self.assertIn("现在配置 Worker secrets 吗？", content)
        self.assertIn("CLOUDFLARE_API_TOKEN", content)
        self.assertIn("npm ci", content)
        self.assertIn("npm test", content)
        self.assertIn("npx tsc --noEmit", content)
        self.assertIn("npm run check:worker", content)
        self.assertIn("_worker.js 不存在", content)
        self.assertIn("wrangler secret put", content)
        self.assertIn("wrangler deploy", content)
        self.assertIn("https://$WorkerHost/", content)
        self.assertIn("[AllowEmptyString()]", content)
        self.assertIn("NoPause", content)
        self.assertIn("ROCO_DEPLOY_PERSISTENT_WINDOW", content)
        self.assertIn("Start-PersistentConsoleIfNeeded", content)
        self.assertIn("执行结束，按回车键退出", content)
        self.assertIn("Remove-Item Env:CLOUDFLARE_API_TOKEN", content)
        self.assertTrue(script.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_windows_cmd_launcher_keeps_explorer_window_open(self):
        script = ROOT / "scripts" / "deploy-cf-worker.cmd"
        content = script.read_text(encoding="utf-8")

        self.assertIn("deploy-cf-worker.ps1", content)
        self.assertIn("ExecutionPolicy Bypass", content)
        self.assertIn("ROCO_DEPLOY_PERSISTENT_WINDOW", content)
        self.assertIn("-NoPause", content)
        self.assertIn("ROCO_DEPLOY_CMD_NO_PAUSE", content)
        self.assertIn("pause >nul", content)
        self.assertIn(b"\r\n", script.read_bytes())

    def test_windows_cmd_launcher_line_endings_are_preserved_on_linux_ci(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")

        self.assertIn("*.cmd text eol=crlf", attributes)

    def test_linux_deploy_script_contains_expected_safety_and_deploy_steps(self):
        script = ROOT / "scripts" / "deploy-cf-worker.sh"
        content = script.read_text(encoding="utf-8")

        self.assertIn("--mode source|worker-js", content)
        self.assertIn("deploy_mode", content)
        self.assertIn("source", content)
        self.assertIn("worker-js", content)
        self.assertIn("ask_yes_no", content)
        self.assertIn("请选择部署方式", content)
        self.assertIn("npx 编译/项目部署", content)
        self.assertIn("直接部署项目内 _worker.js", content)
        self.assertIn("现在配置 Worker secrets 吗？", content)
        self.assertIn("read -r -s", content)
        self.assertIn("CLOUDFLARE_API_TOKEN", content)
        self.assertIn("npm ci", content)
        self.assertIn("npm test", content)
        self.assertIn("npx tsc --noEmit", content)
        self.assertIn("npm run check:worker", content)
        self.assertIn("_worker.js 不存在", content)
        self.assertIn("wrangler secret put", content)
        self.assertIn("wrangler deploy", content)
        self.assertIn("https://${worker_host}/", content)
        self.assertIn("unset CLOUDFLARE_API_TOKEN", content)

    def test_readme_documents_one_click_deploy_and_update_flow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("一键脚本部署", readme)
        self.assertIn("scripts/deploy-cf-worker.ps1", readme)
        self.assertIn("scripts/deploy-cf-worker.cmd", readme)
        self.assertIn("scripts/deploy-cf-worker.sh", readme)
        self.assertIn("默认交互式", readme)
        self.assertIn("右键/双击", readme)
        self.assertIn("按回车键退出", readme)
        self.assertIn("npx 编译/项目部署", readme)
        self.assertIn("_worker.js 直接部署", readme)
        self.assertIn("-DeployMode Source", readme)
        self.assertIn("--mode worker-js", readme)
        self.assertIn("CLOUDFLARE_API_TOKEN", readme)
        self.assertIn("后续更新", readme)
        self.assertIn("ROCOM_API_KEY", readme)
        self.assertIn("SERVERCHAN_SENDKEY", readme)


if __name__ == "__main__":
    unittest.main()
