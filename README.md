<div align="center">
    <a href="https://log1997.github.io/log-lottery/">
        <img src="./static/images/lottery.png" width="100" height="100" />
    </a>

# log-lottery 🚀🚀🚀🚀

[![github stars](https://img.shields.io/github/stars/log1997/log-lottery)](https://github.com/LOG1997/log-lottery)
[![version](https://img.shields.io/github/package-json/v/log1997/log-lottery)](https://github.com/LOG1997/log-lottery)
[![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/LOG1997/log-lottery)
[![github author](https://img.shields.io/badge/Author-log1997-blue.svg)](https://github.com/log1997)
[![build](https://img.shields.io/github/actions/workflow/status/log1997/log-lottery/release.yml)](https://github.com/log1997)
[![docker](https://img.shields.io/docker/pulls/log1997/log-lottery)](<https://hub.docker.com/r/log1997/log-lottery>)
[![github downloads](https://img.shields.io/github/downloads/log1997/log-lottery/total)](https://github.com/LOG1997/log-lottery/releases)
[![release data](https://img.shields.io/github/release-date/log1997/log-lottery)](https://github.com/LOG1997/log-lottery/releases)
[![last commit](https://img.shields.io/github/last-commit/log1997/log-lottery/dev)](https://github.com/LOG1997/log-lottery/commits/dev/)
</div>

log-lottery 是一个可配置、可定制、可部署的抽奖系统，支持炫酷 3D 大屏抽奖，也支持完整后台业务管理（项目、人员、奖项、规则、导出）。

> 如果进入网站遇到图片无法显示或有报错的情况，请先到【全局配置】-【界面配置】菜单中点击【重置所有数据】按钮清除数据后进行更新。

> 支持在 Django Admin 执行内定中奖（支持单人指定与批量手机号）

## 项目亮点

- 抽奖业务闭环：支持抽奖预览、确认、作废，保留审计轨迹。
- 大屏展示能力：3D 球体抽奖动画、主题/图案配置、背景图与音乐管理。
- 配置化管理：人员、奖项、排除规则、导出任务均可在后台配置。
- 多端协作架构：前端 Vue 大屏 + Django API。
- 生产可部署：支持 Docker，也提供 Nginx/systemd/环境变量模板。

## 核心功能

### 1) 抽奖流程管理

- 支持创建抽奖批次并预览结果（`PENDING`）。
- 支持确认批次并落库（`CONFIRMED`），同步更新奖项已用数量。
- 支持作废未确认批次（`VOID`），保留历史记录便于追溯。

### 2) 人员与奖项配置

- 支持 Excel/CSV 导入参与人员，支持名单管理与状态维护。
- 支持奖项名称、数量、排序、全员参与、分批抽取等配置。
- 支持排除规则配置（跨项目/跨奖项排除）。

### 3) 现场展示与互动

- 3D 球体抽奖主界面，支持实时开奖展示。
- 支持自定义标题、卡片布局、主题样式与界面图案。
- 支持背景音乐、背景图片上传与切换。

### 4) 结果留存与导出

- 支持中奖结果查询与后台管理。
- 支持导出任务创建与文件下载，便于活动复盘归档。

### 5) 运维与部署

- 前端静态资源可独立部署，默认路径 `/log-lottery/`。
- Django 提供 `/api/*` 及 `/admin/` 管理端能力。
- 已提供部署材料：Nginx 反代、systemd 服务、生产环境变量模板。

## 要求

使用PC端最新版Chrome或Edge浏览器。

访问地址：

<https://lottery.to2026.xyz/log-lottery>

or

<https://log1997.github.io/log-lottery/>

如果想要访问2025年12月31日前的版本，请前往：<https://to2026.xyz/log-lottery>

需要更多功能或发现 bug，请提交 [issues](https://github.com/LOG1997/log-lottery/issues)。

## 预览

首页
<div align="center">
    <img src="./static/images/home.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
    <img src="./static//images/home_prizelist.png" alt="img2-2" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
</div>

抽奖
<div align="center">
    <img src="./static/images/lottery-enter.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
    <img src="./static/images/lottery-done.png" alt="img2-2" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
</div>

配置
<div align="center">
    <img src="./static/images/config_personall.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
    <img src="./static/images/config_prize.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
    <img src="./static/images/config-view.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
    <img src="./static/images/config_pattern.png" alt="img2-1" width="400" style="border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 8px;">
</div>

图片音乐配置

## 技术

- vue3
- threejs
- indexdb
- pinia
- daisyui

## 开发

安装依赖

```bash
pnpm i
or
npm install
```

开发运行

```bash
pnpm dev
or
npm run dev
```

打包

```bash
pnpm build
or
npm run build
```

> 项目思路来源于 <https://github.com/moshang-xc/lottery>

## 部署指南（前后端）

- 跨平台完整部署（Windows + Linux）：[`docs/DEPLOYMENT_GUIDE_WINDOWS_LINUX.md`](./docs/DEPLOYMENT_GUIDE_WINDOWS_LINUX.md)
- 后端快速启动（Django + PostgreSQL）：[`backend/README.md`](./backend/README.md)
- 生产部署材料包（Nginx/systemd/env 模板）：[`docs/DEPLOYMENT_MATERIALS_2026-03-12.md`](./docs/DEPLOYMENT_MATERIALS_2026-03-12.md)
- Docker 低配部署（本地构建镜像再上服务器）：[`docs/DEPLOYMENT_DOCKER_LOW_RESOURCE_2026-03-19.md`](./docs/DEPLOYMENT_DOCKER_LOW_RESOURCE_2026-03-19.md)

## Docker支持

1. 完整部署（前端 + Django，推荐）

    ```bash
    bash scripts/docker_local_build_test.sh
    ```

    镜像导出并部署到服务器：

    ```bash
    bash scripts/docker_export_images.sh
    # 服务器上执行
    bash scripts/docker_server_load_and_up.sh /path/to/log-lottery-images.tar.gz
    ```

2. 仅前端静态页面（历史兼容方式）

    ```bash
    docker build -t log-lottery .
    docker run -d -p 9279:80 log-lottery
    ```

    容器启动后访问：<http://localhost:9279/log-lottery/>

## 发布产物

可前往[Releases](https://github.com/LOG1997/log-lottery/releases)下载。

发布产物为前端构建压缩包（`dist.zip`）。

## 支持项目

<h3>💝 赞助支持</h3>

<p><em>如果您觉得 log-lottery 对您有帮助，欢迎赞助支持，您的支持是我们不断前进的动力！</em></p>

<div>
 <img src="./static/images/ZanShang.png" height="240" alt="WeChat Code">
</div>

<br>

## Contributors

Thanks to all the people who have contributed to this project!

[![Contributors](https://contrib.rocks/image?repo=log1997/log-lottery)](https://github.com/LOG1997/log-lottery/graphs/contributors)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=LOG1997/log-lottery&type=Date)](https://star-history.com/#LOG1997/log-lottery&Date)

## License

[MIT](http://opensource.org/licenses/MIT)
