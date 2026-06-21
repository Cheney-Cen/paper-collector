# Feedback Worker

Cloudflare Pages 负责只读仪表盘；这个 Worker 负责把经过 Access 认证的反馈写入私有 GitHub 仓库的 `data/feedback/`。

## GitHub 与 Cloudflare 配置

- GitHub Secret `CLOUDFLARE_API_TOKEN`：Cloudflare API Token，需要 **Account / Cloudflare Pages: Edit** 与 **Account / Workers Scripts: Edit** 权限。
- GitHub Secret `CLOUDFLARE_ACCOUNT_ID`：Cloudflare Dashboard 右侧可见的 Account ID。
- GitHub Secret `WORKER_GITHUB_TOKEN`：Fine-grained PAT，只授予本私有仓库 **Contents: Read and write** 权限；不要使用你的主 GitHub 密码。
- GitHub Secret `CF_ACCESS_AUD`：Cloudflare Access application audience。
- GitHub Variable `CLOUDFLARE_PAGES_PROJECT`：Cloudflare Pages 项目名，例如 `paper-collector`。
- GitHub Variable `CF_ACCESS_TEAM_DOMAIN`：例如 `your-team.cloudflareaccess.com`。
- GitHub Variable `FEEDBACK_ALLOWED_ORIGIN`：仪表盘的完整 HTTPS origin，例如 `https://paper-collector.pages.dev`。

工作流会自动注入 `GITHUB_REPOSITORY`，并把 `WORKER_GITHUB_TOKEN` 写成 Worker secret。

在 Worker 上设置 `FEEDBACK_ALLOWED_ORIGIN` 为 Pages 的准确 HTTPS origin。Worker 会验证 Access JWT 的签名、Audience 和 issuer；浏览器不接触 GitHub 令牌。

## 部署顺序

1. 在 Cloudflare Pages 创建项目并设置项目名；项目的生产分支选择 `main`。
2. 在 Cloudflare Zero Trust 创建一个 Access application，先保护 Pages 的 HTTPS hostname；登录策略只允许你的邮箱或身份提供商账号。
3. 在 GitHub 按上方清单设置 secrets/variables，手动运行 **Collect daily papers**，它会发布 `site/` 到 Pages。
4. 手动运行 **Deploy feedback worker**，记录输出中的 `workers.dev` URL；把它填入 `site/config.js` 的 `PAPER_COLLECTOR_FEEDBACK_ENDPOINT` 后提交。
5. 在同一个 Access application 中再加入该 Worker hostname。这样仪表盘与反馈接口都要求登录。

Worker 会验证 Access JWT 的签名、Audience 和 issuer；浏览器不接触 GitHub 令牌。
