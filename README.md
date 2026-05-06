# Event Trading Analysis System

基于大语言模型的事件驱动交易分析系统，通过分析国际重大事件，推理产业链传导路径，生成投资信号。

## 功能特性

- **事件理解**: LLM 自动识别事件类型、核心实体、市场情绪
- **产业链传导**: 自动推理事件在产业链中的传导路径
- **交易信号**: 生成 BUY/SELL 信号及置信度
- **流式响应**: 实时展示 LLM 推理过程
- **可视化展示**: 传导链可视化、情绪仪表盘

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Next.js)                        │
│   事件输入 → 流式展示 → 传导链可视化 → 交易信号                │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                       后端 (FastAPI)                         │
│   API → LLM事件分析 → 传导引擎 → 信号生成                     │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider                            │
│              (Claude / OpenAI / Ollama)                      │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+
- LLM API Key (Claude / OpenAI)

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 运行
python -m uvicorn app.main:app --reload --port 8080
```

### 3. 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

### 4. 访问

打开浏览器访问 http://localhost:3000

## Docker 部署 (VPS)

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 环境变量

### 后端 (.env)

```env
# LLM 配置 (选择一种)
ANTHROPIC_API_KEY=your_claude_api_key
# 或
OPENAI_API_KEY=your_openai_api_key

# LLM Provider
LLM_PROVIDER=claude  # openai / ollama
```

### 前端 (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8080
```

## API 接口

### 分析事件

```bash
POST /api/v1/analyze
Content-Type: application/json

{
  "title": "美国与伊朗爆发军事冲突",
  "content": "详细描述...",
  "use_cache": true
}
```

### 流式分析

```bash
POST /api/v1/analyze/stream
# 返回 Server-Sent Events
```

### 获取示例事件

```bash
GET /api/v1/examples
```

## 项目结构

```
event-trading-system/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── config.py       # 配置
│   │   ├── schemas/        # 数据模型
│   │   └── services/       # 业务逻辑
│   │       ├── llm_client.py   # LLM 封装
│   │       ├── prompts.py      # Prompt 模板
│   │       └── analysis.py     # 事件分析服务
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js 页面
│   │   ├── components/    # React 组件
│   │   ├── hooks/         # 自定义 Hooks
│   │   └── types/         # TypeScript 类型
│   ├── package.json
│   └── tailwind.config.js
│
└── docker-compose.yml
```

## 使用示例

### 输入事件

```
美国与伊朗爆发军事冲突，伊朗封锁霍尔木兹海峡
```

### 系统输出

1. **事件理解**: 地缘政治事件，情绪 -0.8 (极度利空)
2. **直接受影响**: 原油供给减少 → 石油开采行业利好
3. **传导链**:
   - Step 1: 原油 → 石油加工 (成本传导, 70%, 3天)
   - Step 2: 石油加工 → 化工 (成本传导, 60%, 7天)
   - Step 3: 原油 → 航运 (成本传导, 80%, 1天)
   - Step 4: 航运 → 航空 (成本传导, 70%, 5天)
4. **交易信号**:
   - 做多: 中国石油 (601857.SH) - 置信度 85%
   - 做空: 航空股 - 置信度 75%

## 技术栈

- **后端**: FastAPI, Python 3.11+, Pydantic, OpenAI/Anthropic SDK
- **LLM 支持**: OpenAI / Claude / Ollama / **SiliconFlow (硅基流动)**
- **前端**: Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts
- **部署**: Docker, Docker Compose

## License

MIT
