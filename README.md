# SGMessengerBot - Telegram 转发机器人

一个简单的 Telegram 机器人，用于将用户消息转发给管理员，管理员可以回复消息转发给用户。

---

## ✨ 功能特点

- 📩 消息转发：将用户消息转发给管理员  
- 🔁 管理员回复：支持管理员回复用户消息  
- ✅ 用户验证：防止机器人滥用  
- 🧵 话题管理：在群组中为每个用户创建独立话题  
- 📢 全体广播：管理员可向所有用户发送广播消息  

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置机器人

复制配置文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入如下配置：

```env
# 从 @BotFather 获取
BOT_TOKEN=你的机器人Token

# 从 @userinfobot 获取
OWNER_ID=你的用户ID

# 论坛群组ID（需要先创建论坛群组）
GROUP_ID=群组ID
```

---

## 🔧 准备工作

### 创建机器人

1. 找到 [@BotFather](https://t.me/BotFather)  
2. 发送 `/newbot` 创建机器人  
3. 获取 Bot Token

### 获取用户 ID

1. 使用 [IDBot](https://t.me/username_to_id_bot)  
2. 获取自己的 ID 和群 ID

### 创建论坛群组

1. 创建新群组  
2. 在群组设置中启用「话题」功能  
3. 将机器人添加为管理员  
4. 给机器人「管理话题」权限  

---

## ▶️ 运行机器人

```bash
python main.py
```

---

## 📦 1Panel 简易教程

![1Panel 教程图1](https://cdn.nodeimage.com/i/riW2Pe49EPzbP0sScXg0KmtU0p2AtN2Z.png)  
![1Panel 教程图2](https://cdn.nodeimage.com/i/Dw5Fhmyn960zK3N0MBE1YkyZXkS3zlaK.png)

### 启动命令：

```bash
pip install -r requirements.txt && python main.py
```

---

## 📚 关于项目

- 项目由 AI 编写，功能简单  
- 欢迎自行修改扩展功能  
- 电报交流群：[https://t.me/SGMki](https://t.me/SGMki)

> 一分也爱 ❤️  
> ![一分也爱](https://cdn.nodeimage.com/i/MRGHwUfa9rkuqNxpw0AbGYd8lQHtNYYA.webp)

---

## 📄 许可证

MIT License
