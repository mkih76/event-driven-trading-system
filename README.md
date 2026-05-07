# Event Trading Analysis System

基于大语言模型的事件驱动交易分析系统，通过分析国际重大事件，推理产业链传导路径，生成投资信号。

## 功能特性

- **事件理解**: LLM 自动识别事件类型、核心实体、市场情绪
- **产业链传导**: 自动推理事件在产业链中的传导路径（成本传导 / 需求传导 / 替代效应）
- **交易信号**: 生成做多/做空信号及置信度
- **流式响应**: 实时展示 LLM 推理过程（SSE）
- **可视化**: SVG 交互式传导图谱、情绪仪表盘、历史回测
- **多 LLM 支持**: SiliconFlow（推荐）/ OpenAI / Claude / Ollama
- **RAG 增强**: 实时市场数据上下文注入分析

## 一键部署到 VPS

```bash
# SSH 登录 VPS 后，一行命令完成部署
bash <(curl -sL https://raw.githubusercontent.com/mkih76/event-driven-trading-system/master/deploy.sh)
```

**最低配置**: 1核 1G（推荐 2G+） | **推荐系统**: Ubuntu 20.04+

---

## 本地开发

### 环境要求

- Python 3.11+、Node.js 18+、Docker（可选）

### Docker 部署（本地 / VPS 通用）

```bash
git clone https://github.com/mkih76/event-driven-trading-system.git
cd event-driven-trading-system

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 SILICONFLOW_API_KEY（推荐：https://cloud.siliconflow.cn）

# 启动
docker-compose up -d

# 访问
open http://localhost
```

### 手动部署

**后端：**
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env && vi .env  # 填入 API Key
uvicorn app.main:app --reload --port 8080
```

**前端：**
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:3000
```

---

## 快速演示

输入事件示例：

```
美国与伊朗爆发军事冲突，伊朗封锁霍尔木兹海峡
```

系统将输出：

1. **事件理解**: 地缘政治事件，情绪 -0.85（极度利空）
2. **直接受影响**: 原油 → 供给减少，利好石油开采
3. **传导链**:
   - 原油 → 石油加工（成本传导, 70%, 3天）
   - 石油加工 → 化工（成本传导, 60%, 7天）
   - 原油 → 航运（成本传导, 80%, 1天）
   - 航运 → 航空（成本传导, 70%, 5天）
4. **交易信号**: 做多石油股（置信度 85%）、做空航空股（置信度 75%）

---

## API 接口

```bash
# 普通分析
POST /api/v1/analyze
{ "title": "美国与伊朗爆发军事冲突", "content": "..." }

# 流式分析（SSE）
POST /api/v1/analyze/stream

# 示例事件
GET /api/v1/examples

# 健康检查
GET /health
```

---

## 项目结构

```
event-trading-system/
├── deploy.sh              # VPS 一键部署脚本
├── docker-compose.yml     # 容器编排（含 Nginx 反向代理）
├── nginx.conf             # Nginx 配置（HTTP + HTTPS 模板）
├── .env.example           # 环境变量模板
│
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 配置
│   │   ├── schemas/          # Pydantic 数据模型
│   │   └── services/
│   │       ├── llm_client.py  # 多 LLM 封装 + 降级机制
│   │       ├── prompts.py     # Prompt 模板
│   │       ├── analysis.py    # 事件分析服务
│   │       ├── rag_service.py # RAG 实时上下文
│   │       ├── network_graph.py
│   │       └── causal_reasoning/   # 因果推理模块
│   │       └── signal_output/       # 信号解释模块
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── app/page.tsx          # 主页面
    │   ├── components/
    │   │   ├── TransmissionGraph.tsx  # SVG 传导图谱
    │   │   ├── DegradationBanner.tsx # 降级提示
    │   │   └── Sidebar.tsx
    │   ├── hooks/useAnalysis.ts  # API Hook
    │   └── types/index.ts
    └── Dockerfile
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI · Python 3.11+ · Pydantic · uvicorn |
| LLM | SiliconFlow · OpenAI · Claude · Ollama |
| 前端 | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| 容器 | Docker · Docker Compose · Nginx |
| 部署 | Ubuntu / Debian · Let's Encrypt |

---

## VPS 部署后管理

```bash
# 进入目录
cd /opt/event-trading-system

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 更新代码
git pull && docker-compose up -d --build

# 停止服务
docker-compose down

# SSL 证书续期（Let's Encrypt 证书有效期 90 天，自动续期已配置）
certbot renew --dry-run
```

如遇问题，先查日志：
```bash
docker-compose logs backend   # 后端日志
docker-compose logs frontend  # 前端日志
docker-compose logs nginx     # Nginx 日志
```

## License

MIT
