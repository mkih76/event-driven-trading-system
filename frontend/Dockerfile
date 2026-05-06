FROM node:18-alpine

WORKDIR /app

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制代码
COPY . .

# 构建
RUN npm run build

# 运行
CMD ["npm", "start"]
