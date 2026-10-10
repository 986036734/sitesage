# Devpost 草稿填写内容（Nebius x NVIDIA Global AI Hackathon）
# 草稿地址：https://devpost.com/submit-to/30790-nebius-x-nvidia-global-ai-hackathon/manage/submissions/1227668/project-overview
# 注意：只填草稿，不要点最终 Submit

## Project name（≤60 字符）
SiteSage — Chat with Any Website

## Elevator pitch（≤200 字符）
Paste any URL and chat with the page. SiteSage extracts the content and answers your questions with citations, powered by NVIDIA Nemotron on Nebius Token Factory.

## Thumbnail
待定：用应用截图（1200x800）制作

## About the project（Markdown）
# Inspiration
Reading long docs, papers, and articles is slow. We wanted a way to *talk* to any web page — paste a link, ask questions, get cited answers in seconds.

# What it does
**SiteSage** turns any web page into a conversation:
- Paste a URL → the page is fetched, cleaned, and chunked automatically
- Get an instant TL;DR summary plus AI-suggested questions
- Ask anything — answers cite their sources as [1], [2], …
- Smart model routing: quick questions go to the fast Nemotron Nano model, complex ones to the deep reasoning model (or pick manually)

# How we built it
- **Frontend**: single-page app, no build step (HTML/CSS/vanilla JS)
- **Backend**: Python FastAPI + SQLite; `trafilatura` for article extraction, lightweight token-overlap retrieval
- **AI**: every answer is a runtime call to the **Nebius Token Factory** OpenAI-compatible inference API (`POST /v1/chat/completions`) using **NVIDIA Nemotron** open-source models (`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` for fast calls, `nvidia/Nemotron-3-Ultra-550b-a55b` for deep reasoning). Token Factory is what the app runs on — zero GPUs of our own.

# Challenges we ran into
- Extracting clean text from JS-heavy pages (fallback to raw fetch when readability extraction fails)
- Keeping answers grounded: the system prompt forces citations and "say you don't know" instead of hallucinating
- Stretching $1 of trial credits: model routing sends trivial work to the cheapest fast model

# What's next
- Tavily web-search fallback for questions the page can't answer
- Multi-page collections ("chat with this whole docs site")
- Shareable session links

## Built with（标签）
Python, FastAPI, NVIDIA Nemotron, Nebius Token Factory, SQLite, JavaScript, HTML/CSS

## Demo video URL
待定（视频制作中，见 demo-video/ 目录说明）

## Try it out 链接
http://51.103.47.12:8001/ （部署后确认）

## Track
Best Apps and Agents

## 能否到 NVIDIA 总部现场
No

## 是否愿意参加决赛面试
Yes

## 反馈（给 Nebius 的 feedback 字段，按需填写）
Token Factory's OpenAI-compatible API made integration trivial — swapped base URL and model name and it just worked. Would love a models.list filter by vendor to discover Nemotron models faster.
