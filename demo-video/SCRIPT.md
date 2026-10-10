# SiteSage 演示视频脚本（≤3 分钟，YouTube 公开）
# 目标地址：http://51.103.47.12:8001/（录制前确认服务正常 + NEBIUS_API_KEY 已配置）
# 录制：浏览器 1280x800，录屏 + 英文旁白（或字幕）

## Shot 1（0:00–0:20）开场
- 画面：SiteSage 首页
- 旁白："Meet SiteSage — chat with any website. Paste a link, ask questions, get cited answers in seconds. It's powered by NVIDIA Nemotron models running on Nebius Token Factory."

## Shot 2（0:20–0:50）加载页面
- 操作：在输入框粘贴 `https://docs.tokenfactory.nebius.com/quickstart`，点 Load page
- 画面：显示标题、3-sentence TL;DR 摘要、3 个 AI 推荐问题 chips
- 旁白："I paste a docs page. SiteSage fetches it, extracts the content, writes a summary, and even suggests questions — all with Nemotron 3 Nano, the fast model."

## Shot 3（0:50–1:40）提问（核心演示）
- 操作：点一个推荐问题 chip（或输入 "What models are available on Token Factory?"），选 Deep 模式再问一个复杂问题如 "How do I authenticate API requests?"
- 画面：回答逐条出现，带 [1][2] 引用标注；注意模型标签显示 "via Nemotron-3-Ultra-550b-a55b"
- 旁白："Every answer is grounded in the page with citations — no hallucinations. Simple questions use the fast Nano model; complex ones are routed to Nemotron 3 Ultra for deep reasoning."

## Shot 4（1:40–2:10）换个页面
- 操作：粘贴一篇英文新闻/博客 URL，问一个该页面特有的问题
- 旁白："It works on any website — docs, articles, blogs. Each page gets its own chat session with history."

## Shot 5（2:10–2:40）技术说明
- 画面：切到 GitHub 仓库 README（或终端 curl /api/health）
- 旁白："Under the hood: FastAPI backend, zero GPUs of our own — every model call is a runtime request to Nebius Token Factory's OpenAI-compatible API using NVIDIA open-source Nemotron models."

## Shot 6（2:40–3:00）收尾
- 画面：回到应用首页
- 旁白："SiteSage — stop skimming, start asking. Built for the Nebius x NVIDIA Global AI Hackathon."

## 录制检查清单
- [ ] http://51.103.47.12:8001/ 可访问
- [ ] /api/health 显示 "llm_configured": true
- [ ] 准备 2 个演示 URL（docs 页 + 1 篇文章页）
- [ ] 时长 < 3:00，无版权音乐
- [ ] 上传 YouTube 设为公开，把链接填回 Devpost 草稿
