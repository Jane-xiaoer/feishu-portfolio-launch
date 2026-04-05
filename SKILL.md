---
name: feishu-portfolio-launch
description: 从飞书多维表格链接出发，边操作边引导，最终把作品集网站上线到 GitHub Pages + 自定义域名。适用于视频/图片附件存在飞书、需要对外展示的创作者（AI视频、摄影、设计、样片库等）。不适合博客、电商、需要后端写入的场景。
---

# Feishu Portfolio Launch

## 这个 Skill 做什么

**一句话：给我飞书多维表格链接，我带你把作品集网站上线。**

整个过程我会一步一步引导，你只需要：
- 告诉我飞书表格链接
- 选择网站风格
- 在浏览器确认预览效果
- 在 DNS 控制台添加几条记录（5分钟，可选）

其他的技术活全部我来。

---

## 适用网站类型

✅ **适合**
- AI 视频 / 图片作品集（附件在飞书多维表格）
- 摄影、设计、创意样片库
- 客户案例展示站
- 任何「内容存飞书 → 对外展示」的场景

❌ **不适合**
- 图文博客（没有文件附件）
- 电商、支付、用户注册
- 需要实时写入数据库的场景

**核心限制说明：** 飞书视频/图片临时播放链接 24 小时过期。Skill 会在你的 Mac 上设置自动刷新脚本（每 20 小时跑一次，10 秒完成），Mac 需要保持开机。

---

## 执行流程

### Step 0：环境检查（自动）

第一件事，检查所有工具是否就绪：

```bash
for cmd in node python3 gh git; do
  which $cmd > /dev/null 2>&1 && echo "✅ $cmd" || echo "❌ $cmd 缺失"
done
lark-cli --version > /dev/null 2>&1 && echo "✅ lark-cli" || echo "❌ lark-cli 缺失"
lark-cli whoami > /dev/null 2>&1 && echo "✅ 飞书已授权" || echo "⚠️  飞书未授权"
gh auth status > /dev/null 2>&1 && echo "✅ GitHub 已登录" || echo "⚠️  GitHub 未登录"
```

**如果有缺失，告诉用户发给 Claude Code 的指令：**

> 帮我在这台 Mac 上安装：lark-cli（飞书命令行工具，npm 包）、gh（GitHub CLI）。需要的话先装 Node.js。装好后帮我完成飞书登录（lark-cli login）和 GitHub 登录（gh auth login）。

等用户确认「全部 ✅」后再继续。

---

### Step 1：导出飞书数据

**向用户提问：**

> 请把你的飞书多维表格链接发给我。
> 格式类似：`https://xxx.feishu.cn/base/AbCdEfGhIj`

拿到链接后，解析 app_token（/base/ 后面那串）。

**询问字段信息：**
> 你的视频/图片存在哪个字段里？（发给我字段名，通常叫「样片」「附件」「视频」之类）
> 另外，你希望网站上展示哪些信息？（比如标题、分类、时长、使用的 AI 工具……把你有的字段名告诉我）

**自动执行导出：**

```bash
APP_TOKEN="[解析出来的 token]"

# 先查表格列表，拿 table_id
lark-cli api GET "/open-apis/bitable/v1/apps/${APP_TOKEN}/tables" \
  > /tmp/feishu_tables.json

# 导出第一个表的所有记录（如有多个表让用户选）
TABLE_ID="[第一个或用户选的]"
lark-cli api GET "/open-apis/bitable/v1/apps/${APP_TOKEN}/tables/${TABLE_ID}/records" \
  --params '{"page_size": 100}' \
  > /tmp/feishu_records.json
```

**自动提取 file_token 和字段数据：**

```python
import json

with open('/tmp/feishu_records.json') as f:
    data = json.load(f)

records = data['data']['items']
all_tokens = []
clean_records = []

for r in records:
    fields = r.get('fields', {})
    tokens_in_record = []
    
    for key, val in fields.items():
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict) and 'file_token' in item:
                    tokens_in_record.append(item['file_token'])
                    all_tokens.append(item['file_token'])
    
    if tokens_in_record:
        clean_records.append({
            'tokens': tokens_in_record,
            'fields': fields
        })

print(f"找到 {len(clean_records)} 条记录，{len(all_tokens)} 个附件 file_token")
```

**向用户展示结果，等确认：**
> 我找到了 N 条记录、M 个视频/图片附件。字段有：[列出字段名]。这些数据齐全吗？确认后我开始生成网页。

---

### Step 2：生成 HTML 网页

**向用户询问风格（必选一个）：**

```
我要帮你生成网站，先选个风格：

A. 暖色系 Aesop 风  → 米白底 + 琥珀色调，适合艺术/时尚/创意类
B. 极简冷色系        → 白底 + 深灰，适合商业/科技/纪录片类
C. 深色沉浸感        → 黑底 + 金色，适合电影/视觉艺术类
D. 自定义            → 告诉我你想要的感觉
```

**询问布局细节（快速确认，可跳过用默认值）：**

```
默认布局是：4列瀑布流 + 顶部分类筛选 + 点击播放。
要改吗？（不改就直接说"用默认的"）
```

**自动生成 index.html：**

根据飞书数据和用户选择的风格，生成单页 HTML，要求：
- 所有附件用 `data-token="file_token"` 存储，不直接放 src
- 页面加载时 `fetch('/api/videos.json')` 填充播放链接
- inline CSS（不依赖外部 CSS 框架，不用 flex/grid 以保证兼容性）
- 分类筛选按钮（根据飞书数据中的分类字段自动生成）
- 响应式：桌面4列、平板2列、手机1列（用 float 或百分比宽度）
- 出错时优雅降级（视频加载失败显示占位图，不崩溃）

**让用户预览：**

```bash
# 用默认浏览器打开本地预览
open index.html
```

> 我已生成 index.html 并打开了预览。看看效果，告诉我要改什么（颜色、字体、间距、卡片样式……随便说），改到满意了再继续。

等用户说「可以了」或「发布吧」之类才继续。

---

### Step 3：GitHub 上线

**询问用户：**
> 你的 GitHub 用户名是？仓库想叫什么名字？（默认用 `portfolio`）

**自动执行：**

```bash
GH_USER="[用户名]"
REPO_NAME="[仓库名]"
PROJECT_DIR="[项目目录]"

cd $PROJECT_DIR

# 创建 GitHub 仓库（公开，Pages 才能免费用）
gh repo create $REPO_NAME --public --source=. --remote=origin --push

# 开启 GitHub Pages
gh api -X POST /repos/$GH_USER/$REPO_NAME/pages \
  -f source[branch]=main \
  -f source[path]=/

echo "网站地址：https://$GH_USER.github.io/$REPO_NAME"
```

**等待并告知：**
> 代码已上传，GitHub Pages 正在构建，通常 2-5 分钟后可以访问：
> **https://[用户名].github.io/[仓库名]**
> 
> 先等一下，我告诉你视频还不能播，因为还没跑刷新脚本。

---

### Step 4：自动刷新视频链接

**说明：**
> 现在网站上线了但视频还播不了——飞书的播放链接需要临时获取，而且 24 小时后失效。接下来我给你的 Mac 设一个定时任务，每 20 小时自动换新链接，推到 GitHub。

**自动生成 `scripts/refresh-videos.py`：**

填入从 Step 1 提取的所有 file_token，脚本逻辑：
1. 分批（每批5个）调用飞书 API 获取临时下载 URL
2. 写入 `api/videos.json`
3. Git commit + push 到 GitHub

（代码结构参考 `/Users/jane/projects/xiaoerai-portfolio/scripts/refresh-videos.py`，直接复用这个经过验证的版本，替换 ALL_TOKENS 列表和路径变量。）

**自动检测 nvm node 路径：**

```bash
# 找到 lark-cli 实际使用的 node
NODE_PATH=$(which node)
LARK_PATH=$(which lark-cli)
echo "node: $NODE_PATH"
echo "lark-cli: $LARK_PATH"
```

**自动生成并注册 launchd plist：**

```bash
PLIST_LABEL="[反域名].refresh-videos"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
SCRIPT_PATH="$PROJECT_DIR/scripts/refresh-videos.py"
LOG_PATH="$HOME/.logs/refresh-videos.log"
NODE_BIN_DIR=$(dirname $NODE_PATH)

cat > $PLIST_PATH << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$PLIST_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$SCRIPT_PATH</string>
  </array>
  <key>StartInterval</key><integer>72000</integer>
  <key>RunAtLoad</key><false/>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$NODE_BIN_DIR:/usr/local/bin:/usr/bin:/bin</string>
    <key>HOME</key><string>$HOME</string>
  </dict>
  <key>StandardOutPath</key><string>$LOG_PATH</string>
  <key>StandardErrorPath</key><string>$LOG_PATH</string>
</dict>
</plist>
EOF

# 注册
launchctl load $PLIST_PATH

# 立刻测试跑一次
launchctl start $PLIST_LABEL
sleep 15

# 看结果
echo "=== 日志 ==="
tail -20 $LOG_PATH
```

**向用户确认：**
> 日志显示成功了吗？你看到「Pushed.」说明链接已刷新，视频应该可以播了。
> 打开网站试试：https://[地址]

---

### Step 5：域名绑定（可选）

**询问：**
> 要绑定自己的域名吗？有的话现在可以配，没有的话 github.io 地址就够用了。

**如果用户有域名，给出操作指引：**

> 去你的域名控制台（NameSilo / 阿里云 / 腾讯云），添加这几条 DNS 记录：
>
> | 类型 | 主机记录 | 值 |
> |---|---|---|
> | A | @ | 185.199.108.153 |
> | A | @ | 185.199.109.153 |
> | A | @ | 185.199.110.153 |
> | A | @ | 185.199.111.153 |
> | CNAME | www | [用户名].github.io |
>
> 加好之后告诉我你的域名（比如 `mysite.xyz`），我来配 GitHub 那边。

**用户回复域名后，自动执行：**

```bash
DOMAIN="[用户填写]"
echo "$DOMAIN" > $PROJECT_DIR/CNAME
git -C $PROJECT_DIR add CNAME
git -C $PROJECT_DIR commit -m "add: custom domain $DOMAIN"
git -C $PROJECT_DIR push origin main

# GitHub Pages 设置自定义域名
gh api -X PUT /repos/$GH_USER/$REPO_NAME/pages \
  -f cname=$DOMAIN
```

> DNS 生效需要 10 分钟到几小时。生效后用 `https://[域名]` 访问。
> GitHub Pages 会自动申请 HTTPS 证书，完成后地址栏会出现锁。

---

### Step 6：收尾确认

成功后告知用户：

```
✅ 网站已上线：https://[地址]
✅ 自动刷新：每20小时自动换新链接（日志在 ~/.logs/refresh-videos.log）
✅ 以后加新作品：在飞书加一行 → 告诉 Claude Code 新的 file_token → push

下次更新内容时直接说：
「帮我把新视频加到作品集，file_token 是 [xxx]」
```

---

## 关键技术注意点（执行时参考）

| 问题 | 解决方式 |
|---|---|
| lark-cli 每次最多5个 token | 分批调用，每批 BATCH_SIZE=5 |
| launchd 找不到 lark-cli | plist 里 PATH 必须含 nvm node 路径 |
| git push SSL 报错 | 用 `env -i HOME=$HOME PATH=$PATH git push origin main` |
| GitHub Pages 要求公开仓库 | 创建时必须 `--public` |
| 域名生效后 HTTPS 申请失败 | 在 Pages 设置页点「Enforce HTTPS」或等待自动申请 |
| 视频上线后还是播不了 | 检查 api/videos.json 是否已推到 GitHub，检查 fetch 路径是否正确 |
