# feishu-portfolio-launch

**Claude Code Skill** — 给我飞书多维表格链接，我带你把作品集网站全流程上线。

适合把视频/图片作品存在飞书、想对外展示的创作者（AI视频、摄影、设计、样片库等）。

---

## 能做什么

给我一个飞书多维表格链接，我自动完成：

1. **导出飞书数据** — 提取所有附件的 file_token 和字段内容
2. **生成 HTML 网页** — 瀑布流展示，分类筛选，点击播放，并带完整动画层
3. **上线 GitHub Pages** — 免费托管，几分钟可访问
4. **绑定自定义域名**（可选）— DNS 引导 + 自动配置 CNAME
5. **设置自动刷新** — 飞书链接 24 小时过期，由 GitHub Actions 每 12 小时自动换新链接

**你只需要：** 提供表格链接 → 选风格 → 确认预览 → 在 DNS 控制台加几条记录

---

## 适用场景

✅ 视频 / 图片附件存在飞书多维表格  
✅ 想搭一个对外展示的作品集网站  
✅ 不想写代码，全程让 AI 做  

❌ 博客、电商、需要用户注册登录的场景不适合

---

## 安装使用

**方式一：直接复制 SKILL.md**

把 `SKILL.md` 放到你的 Claude Code skills 目录：

```bash
mkdir -p ~/.claude/skills/feishu-portfolio-launch
curl -o ~/.claude/skills/feishu-portfolio-launch/SKILL.md \
  https://raw.githubusercontent.com/Jane-xiaoer/feishu-portfolio-launch/main/SKILL.md
```

**方式二：clone 整个仓库**

```bash
git clone https://github.com/Jane-xiaoer/feishu-portfolio-launch.git \
  ~/.claude/skills/feishu-portfolio-launch
```

安装后，在 Claude Code 里说：

> 「飞书作品集上线」或「帮我用飞书多维表格搭作品集网站」

Claude Code 会自动调用这个 Skill。

---

## 前置条件

开始前需要装好这几个工具（缺什么 Skill 会告诉你怎么补）：

| 工具 | 用途 |
|---|---|
| lark-cli | 访问飞书 API |
| Node.js ≥ 18 | lark-cli 运行环境 |
| Python 3 | 自动刷新脚本 |
| gh (GitHub CLI) | 创建仓库 + 推代码 |
| git | 版本控制 |

需要的账号：飞书、GitHub、域名注册商（可选）

---

## 现在的默认路线

这个 Skill 现在默认采用：

`Feishu Bitable -> refresh.py -> api/*.json -> GitHub Actions -> GitHub Pages`

不再默认依赖本地 `launchd` 或者用户自己的电脑长期开机。

仓库里会生成：

- `refresh.py`
- `.github/workflows/refresh.yml`
- `api/videos.json`
- `api/covers.json`
- `api/portfolio.json`

并要求配置这 4 个 GitHub Secrets：

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_BASE_TOKEN`
- `LARK_TABLE_ID`

Skill 仓库里已经附带可复制模板：

- `assets/refresh.py`
- `assets/refresh.yml`
- `assets/portfolio.sample.json`

前端默认不是纯静态页。这个 Skill 现在会把下面这些动画能力一起作为标准交付：

- hero 首屏入场动画
- sticky 导航 / 筛选条滚动过渡
- 卡片 hover 动效
- 页面或 section reveal 动画
- 需要时接入 Canvas / Three.js 背景动效
- 保留无动画降级，保证内容可读和移动端可用

---

## 实际效果

用这套方法搭出来的网站示例：**[xiaoerai.xyz](https://xiaoerai.xyz)**

- 46 个 AI 视频作品
- 瀑布流布局，分类筛选
- 首屏、卡片、About 页和背景层都有动画
- 飞书链接由 GitHub Actions 自动刷新

---

## License

MIT
