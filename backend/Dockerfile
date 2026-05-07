FROM python:3.11-slim

# 安装系统依赖（curl 用于健康检查）
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY app/ ./app/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8080

# 运行
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
