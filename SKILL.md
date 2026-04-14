---
name: feishu-portfolio-launch
description: 从飞书多维表格链接出发，生成并上线作品集网站到 GitHub Pages，并用 GitHub Actions 定时刷新飞书临时媒体链接。适用于视频/图片附件存在飞书、需要对外展示的创作者（AI 视频、摄影、设计、样片库等）。不适合博客、电商、需要后端写入的场景。
---

# Feishu Portfolio Launch

## 这个 Skill 做什么

一句话：**给我飞书多维表格链接，我把作品集网站搭出来，并把“飞书临时链接会过期”这件事自动化处理掉。**

默认交付物：
- `index.html` 或静态前端页面
- `api/videos.json`
- `api/covers.json`
- `api/portfolio.json`
- `refresh.py`
- `.github/workflows/refresh.yml`

内置模板资源：
- [`assets/refresh.py`](./assets/refresh.py)
- [`assets/refresh.yml`](./assets/refresh.yml)
- [`assets/portfolio.sample.json`](./assets/portfolio.sample.json)

目标结果：
- 网站部署在 GitHub Pages
- 飞书媒体链接由 GitHub Actions 每 12 小时自动刷新
- 用户不用保持自己的电脑开机

---

## 适用场景

✅ 适合：
- AI 视频 / 图片作品集
- 摄影、设计、创意样片库
- 客户案例展示站
- 任何「内容在飞书附件里，前台只负责展示」的场景

❌ 不适合：
- 图文博客
- 电商、支付、登录系统
- 需要数据库写入和后端业务逻辑的网站

---

## 核心原则

**不要把飞书临时 URL 当成永久资源。**

飞书附件的播放 / 下载地址会过期。正确做法不是让用户在本地电脑上定时跑脚本，而是：

1. 从飞书多维表格读取最新记录
2. 调飞书 API 把附件 `file_token` 解析成临时 URL
3. 生成 `api/*.json`
4. 提交回 GitHub 仓库
5. 让 GitHub Pages 自动重新部署

也就是：

`Feishu Bitable -> refresh.py -> api/*.json -> GitHub Pages`

---

## 执行流程

### Step 0：环境检查

先检查本地是否具备初始化所需工具：

```bash
for cmd in node python3 gh git; do
  which "$cmd" >/dev/null 2>&1 && echo "OK  $cmd" || echo "MISS $cmd"
done
lark-cli --version >/dev/null 2>&1 && echo "OK  lark-cli" || echo "MISS lark-cli"
gh auth status >/dev/null 2>&1 && echo "OK  GitHub auth" || echo "MISS GitHub auth"
```

如果缺少工具，再让用户安装。  
如果 `gh` 没登录，先完成 GitHub 登录。

---

### Step 1：拿到飞书 Base 和正确的数据表

向用户要飞书多维表格链接，例如：

`https://my.feishu.cn/base/AbCdEfGhIjk`

从 URL 里解析出 `app_token`。

然后列出所有表：

```bash
lark-cli api GET "/open-apis/bitable/v1/apps/${APP_TOKEN}/tables"
```

**不要默认选第一张表。**  
很多 Base 里会同时存在“空模板表”和“真正有作品的素材表”。要继续读取记录并验证：

- 哪张表有真实附件字段
- 哪张表记录数正确
- 哪张表里字段名是用户要展示的内容

优先找这些字段：
- 视频字段：`样片` / `视频` / `附件`
- 封面字段：`封面` / `封面图` / `海报` / `图片`
- 标题字段：`内容` / `标题` / `作品名称`
- 分类字段：`类型` / `分类`
- 时长字段：`时长`
- 工具字段：`AI工具` / `工具`
- 排序字段：`序号`

如果一张表只有 `文本 / 单选 / 日期 / 附件` 这种空模板字段，继续换表，不要生成网站。

---

### Step 2：验证飞书权限

要让 GitHub Actions 能自动刷新，飞书应用必须至少能：

- 读取多维表记录
- 读取附件媒体链接

执行方案里要显式依赖这 4 个 secrets：

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

如果用户本机已经有可用的飞书应用配置，可以复用。否则要明确告诉用户去飞书开放平台补权限和密钥。

---

### Step 3：导出结构化作品数据

不要只提取 `file_token` 列表。  
应构建一份前端可直接消费的结构化数据，至少包含：

- title
- categories
- duration
- tools
- order
- video_token
- cover_token

推荐输出：

- `api/portfolio.json`：完整作品数组
- `api/videos.json`：`video_token -> tmp_download_url`
- `api/covers.json`：`cover_token -> tmp_download_url`

结构样例可直接参考仓库内的 `assets/portfolio.sample.json`。

前端可以继续用静态 HTML + JS，也可以完全由 `portfolio.json` 渲染。

---

### Step 4：生成前端页面

默认生成静态页面，要求：

- 响应式作品网格
- 分类筛选
- 点击卡片播放
- 全屏放大播放
- 只允许一个视频同时播放
- 封面优先使用飞书封面字段，没有封面时允许退化为无 poster

数据绑定原则：

- HTML 不要写死过期 URL
- 页面运行时拉取 `/api/videos.json` 和 `/api/covers.json`
- 或者直接拉 `/api/portfolio.json` 渲染卡片

如果用户已有站点，优先保留现有视觉样式，只替换数据来源和刷新机制。

---

### Step 5：创建仓库并部署 GitHub Pages

标准流程：

```bash
gh repo create <repo-name> --public --source=. --remote=origin --push
```

然后确认 Pages 来源是：

- branch: `main`
- path: `/`

检查：

```bash
gh api repos/<owner>/<repo>/pages
```

必须确认：
- Pages 已启用
- `cname` 正常（如果有自定义域名）
- source 指向 `main` 和根目录

---

### Step 6：生成自动刷新脚本

刷新脚本应采用下面这条路线：

1. 用 `app_id + app_secret` 换 `tenant_access_token`
2. 读取 Bitable records
3. 从记录里提取视频和封面附件 token
4. 批量调用 `batch_get_tmp_download_url`
5. 写入 `api/videos.json`、`api/covers.json`、`api/portfolio.json`

关键要求：

- 支持分页读取 records
- 批量请求按 5 个 token 一组
- 不要把 token 列表硬编码在脚本里
- 优先从真实表记录动态生成
- 允许多种字段名候选

推荐文件名：

- `refresh.py`

优先直接复制 skill 自带模板：

```bash
cp ~/.claude/skills/feishu-portfolio-launch/assets/refresh.py ./refresh.py
```

然后只修改字段候选数组，不要把具体 token 或具体 URL 硬编码进去。

---

### Step 7：生成 GitHub Actions Workflow

不要再使用本地 `launchd` 作为默认方案。  
默认方案必须是 GitHub Actions。

工作流要求：

- 支持 `workflow_dispatch`
- 支持 `schedule`，默认每 12 小时执行一次
- 执行 `python refresh.py`
- 自动提交 `api/videos.json`、`api/covers.json`、`api/portfolio.json`

标准 secrets：

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

标准文件：

- `.github/workflows/refresh.yml`

优先直接复制 skill 自带模板：

```bash
mkdir -p .github/workflows
cp ~/.claude/skills/feishu-portfolio-launch/assets/refresh.yml .github/workflows/refresh.yml
```

---

### Step 8：把 Secrets 配进仓库

如果当前环境已经有这些值，并且用户明确让你落地，就直接配置：

```bash
gh secret set LARK_APP_ID -R <owner>/<repo>
gh secret set LARK_APP_SECRET -R <owner>/<repo>
gh secret set LARK_BASE_TOKEN -R <owner>/<repo>
gh secret set LARK_TABLE_ID -R <owner>/<repo>
```

然后验证：

```bash
gh secret list -R <owner>/<repo>
```

如果缺值，就停在这里，明确告诉用户缺哪个，不要伪造。

---

### Step 9：手动触发并验证整条链路

完成配置后，立刻手动跑一次 workflow：

```bash
gh workflow run refresh.yml -R <owner>/<repo>
gh run list -R <owner>/<repo> --limit 3
gh run watch <run-id> -R <owner>/<repo> --exit-status
```

再检查线上结果：

```bash
python3 - <<'PY'
import json, urllib.request, time
url = f'https://<domain-or-pages-url>/api/videos.json?t={int(time.time())}'
with urllib.request.urlopen(url, timeout=20) as r:
    data = json.load(r)
print(data.get('_refreshed_at'))
print(data.get('_count'))
PY
```

然后抽测 1 条视频：

- 状态码应为 `206` 或 `200`
- `content-type` 应为 `video/mp4` 或可播放媒体类型

如果线上 `api/videos.json` 还是旧时间：
- 先看 Pages 部署是否完成
- 再看 workflow 是否真的提交了新 JSON
- 再确认 Pages source 是否指向正确分支和目录

---

### Step 10：域名绑定

如果用户要自定义域名，再做：

- `CNAME` 文件
- GitHub Pages custom domain 设置
- DNS 配置引导

这部分沿用 GitHub Pages 标准流程，不需要和飞书逻辑耦合。

---

## 对用户的默认解释

遇到“网站能打开但视频播不了”，优先判断：

1. `api/videos.json` 是否还是旧的
2. 里面的飞书 URL 是否已过期
3. 自动刷新 workflow 是否失败
4. Pages 是否还没重新部署

默认不要先怀疑播放器，也不要先怀疑前端样式。

---

## 成功标准

这个 Skill 完成后，至少要满足：

- 网站已上线
- GitHub Pages 可访问
- 视频可播放
- 仓库里有自动刷新 workflow
- 仓库里已有 4 个 `LARK_*` secrets
- 手动触发 workflow 成功
- 线上 `api/videos.json` 的 `_refreshed_at` 是新时间

---

## 不要再默认做的事

- 不要默认生成本地 `launchd`
- 不要默认依赖用户 Mac 长期开机
- 不要硬编码所有 `file_token`
- 不要只凭第一张表就继续
- 不要只生成 `videos.json`，忽略封面和结构化记录

---

## 参考实现

如果需要一个已经验证过的做法，先直接复用 skill 仓库自带模板：

- `assets/refresh.py`
- `assets/refresh.yml`
- `assets/portfolio.sample.json`

实际项目里最终会生成这些文件：

- `refresh.py`
- `.github/workflows/refresh.yml`
- `api/videos.json`
- `api/covers.json`
- `api/portfolio.json`

优先复用现成仓库模式，再按用户站点样式做适配。
