# 自动休眠服务

一个适合 Windows 局域网环境使用的轻量控制面板。

它把“睡眠 / 定时关机 / 取消关机”做成了一个可网页访问、可托盘常驻、可一键启动、可安装到桌面的轻应用。

## 项目特点

- 局域网网页控制
- 一键启动 `bat`
- Windows 托盘常驻
- 网页账号密码登录
- 支持立即睡眠
- 支持定时关机
- 支持取消关机
- 支持 `PWA` 安装到桌面

## 适用场景

- 在家里或办公室局域网内，远程让自己的电脑睡眠
- 晚上下载完后，定时关机
- 不想每次都开命令行
- 希望像一个本地小应用一样点击使用

## 界面说明

项目现在采用更偏轻应用的界面风格：

- 登录页更像桌面应用入口
- 主页面更接近 `iOS / 小米风格` 的玻璃卡片控制面板
- 浏览器支持时，可以安装到桌面独立打开

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名
```

### 2. 直接双击启动

运行：

- `启动休眠服务.bat`

首次启动会自动：

- 创建 `.venv`
- 安装依赖
- 自动补全 `.env`
- 配置缺失时自动打开 `.env`
- 启动网页服务和托盘

## 访问方式

本机访问：

- `http://127.0.0.1:5000`

局域网内访问：

- `http://你的电脑IP:5000`

## 配置说明

项目使用 `.env` 作为本地配置文件。

主要配置项：

- `SECRET_KEY`
- `APP_USERNAME`
- `APP_PASSWORD`
- `IP_WHITELIST`

示例配置见：

- `.env.example`

示例：

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false

SECRET_KEY=change_me_to_a_random_secret_key
APP_USERNAME=admin
APP_PASSWORD=change_me_password

IP_WHITELIST=
```

## 功能说明

### 睡眠

网页内点击后立即执行。

### 定时关机

提供常用时长选择：

- `5 分钟`
- `30 分钟`
- `1 小时`
- `3 小时`
- `5 小时`
- `立即关机`

### 取消关机

如果已经提交关机计划，可以随时撤销。

## 托盘功能

启动后会常驻托盘，并提供常用操作入口。

当前托盘侧重：

- 打开网页
- 打开配置
- 打开日志
- 开机自启
- 重启服务
- 退出

## PWA / 安装到桌面

本项目支持 `PWA` 基础能力，浏览器支持时可以：

- 安装应用
- 添加到桌面
- 以独立窗口方式打开

常见浏览器里一般可以通过：

- Chrome / Edge 地址栏或菜单中的“安装应用”
- 手机浏览器中的“添加到桌面”

说明：

- 本机 `localhost` 场景下通常更容易正常安装
- 局域网其他设备是否完整支持安装能力，取决于浏览器和是否启用 `HTTPS`

## JSON 接口

登录后，可继续使用接口方式调用。

### 关机

**POST** `/api/system/shutdown`

```bash
curl -X POST http://localhost:5000/api/system/shutdown \
     -H "Content-Type: application/json" \
     -d '{"delay": 30, "force": false}'
```

### 取消关机

**POST** `/api/system/cancel`

```bash
curl -X POST http://localhost:5000/api/system/cancel
```

### 睡眠

**POST** `/api/system/sleep`

```bash
curl -X POST http://localhost:5000/api/system/sleep
```

### 健康检查

**GET** `/api/health`

```bash
curl http://localhost:5000/api/health
```

## 技术栈

- Python
- Flask
- Waitress
- Windows Tray
- HTML / CSS / JavaScript
- PWA Manifest + Service Worker

## 项目来源与致谢

本项目不是从零开始完全独立编写。

它基于以下项目做了二次整理和功能改造：

- 原始项目：`hyang0/shutdown-api`
- 原始地址：`https://github.com/hyang0/shutdown-api`

在原始项目基础上，这个版本主要做了这些调整：

- 改成更适合局域网直接使用的网页登录方式
- 去掉原先依赖 `auth_token` 的使用方式
- 增加 Windows 托盘常驻和一键启动体验
- 增加睡眠控制
- 调整为更适合桌面和移动端的轻应用界面
- 增加 `PWA` 安装到桌面能力

如果你继续基于这个仓库进行二次开发，也建议在自己的项目里保留来源说明。

## 开源前说明

仓库默认忽略以下本地内容：

- `.env`
- `.venv`
- `runtime/`
- `*.log`
- `__pycache__/`

如果你要公开发布，建议确认：

- `.env` 不要提交真实账号密码
- README 中不要保留私人局域网地址
- 如需截图展示，可自行补充项目页面截图

## 许可证

本项目使用 [MIT License](./LICENSE)。

更多来源说明见 [NOTICE](./NOTICE)。
