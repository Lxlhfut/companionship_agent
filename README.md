# 👴 银龄陪伴 · AI Agent 军团

> 基于 Python + LangChain + Streamlit 的智能养老陪伴平台  
> 专为海南自贸港封关背景下的康养产业设计

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=LangChain&logoColor=white)](https://www.langchain.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://python.org)

## 📖 项目简介

**银龄陪伴**是一个面向老年人及其家属的 AI Agent 应用，集成**陪伴聊天、用药提醒、体检报告解读、家人绑定、周边好去处推荐**等核心功能。项目诞生于海南自贸港封关运作的政策红利期，旨在利用 AI 技术降低康养服务门槛，为养老机构、社区服务中心及个人家庭提供智能化的健康管理工具。

> **政策背景**：海南全岛封关后，康养产业被列为重点发展领域。本项目可作为技术原型，快速对接医疗资源、社区服务及跨境电商（进口保健品）等场景，探索“AI + 养老”的创新商业模式。

## ✨ 核心功能

| 模块 | 功能描述 |
|------|----------|
| **💬 陪伴聊天** | 基于大模型的共情对话，支持长期记忆，缓解老人孤独感 |
| **💊 用药提醒** | 自定义用药计划，智能冲突检测，AI 提供服药建议 |
| **📋 体检报告解读** | 上传 PDF 报告，AI 提取关键指标并用通俗语言解释 |
| **👨‍👩‍👧 家人绑定** | 老人与子女双向绑定，共享健康数据与提醒 |
| **🌳 周边好去处** | 搜索公园、医院、景点等，按距离/等级排序，AI 辅助决策 |
| **🏠 个人首页** | 数据仪表盘展示今日用药、家人动态、健康小贴士 |

## 🛠️ 技术栈

- **前端框架**：Streamlit（纯 Python 构建 Web 界面）
- **AI Agent**：LangChain + LangGraph（多智能体协作）
- **大模型接口**：OpenAI 兼容 API（支持 DeepSeek、Claude、GLM 等）
- **向量检索**：Chroma（可选，用于 RAG 知识库）
- **地图服务**：高德地图 API（POI 搜索、地理编码）
- **数据库**：SQLite（轻量级本地存储）
- **部署**：Streamlit Community Cloud / Docker

## 📦 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/companionship-agent.git
cd companionship-agent