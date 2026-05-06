# 项目帮助文档

## 项目概述

`keyword_txt_generator` 是一个基于地区数据库的关键词文本生成工具，主要功能包括：

- 从 `region_db.json` 提取区域数据
- 生成关键词文本文件
- 提供视频移动工具界面
- 支持并发处理和日志输出

## 目录说明

- `main.py`：程序入口
- `config.py`：项目配置项
- `gui.py`：主界面实现
- `region_db.py`：地区数据库加载与管理
- `region_extractor.py`：区域提取逻辑
- `text_generator.py`：关键词文本生成逻辑
- `txt_generator_page.py`：TXT 生成页面界面
- `video_mover.py`：视频移动处理逻辑
- `video_mover_page.py`：视频移动页面界面
- `worker.py`：后台任务和并发调度
- `region_db.json`：地区数据库样本数据

## 快速启动

1. 进入项目目录：

```powershell
cd "c:\Users\Administrator\VS Code Projects\keyword_txt_generator"
```

2. 安装 Python 依赖（如果有）：

```powershell
pip install -r requirements.txt
```

> 如果当前项目没有 `requirements.txt`，请根据实际运行逻辑补充依赖。

3. 运行主程序：

```powershell
python main.py
```

## Claude Code 相关配置

为了提高开发效率，项目中已经添加 VS Code 相关配置，推荐安装 Claude for VS Code 扩展。

### 推荐扩展

- `anthropic.claude-vscode`

### 推荐配置文件

已创建：
- `.vscode/extensions.json`
- `.vscode/settings.json`

### 建议设置

```json
{
  "claude-vscode.apiKey": "",
  "claude-vscode.serverUrl": "https://api.anthropic.com",
  "claude-vscode.model": "claude-3.5-mini",
  "claude-vscode.enableCodeActions": true,
  "claude-vscode.scratchpad.autoSave": true
}
```

请根据实际使用情况，将 `claude-vscode.apiKey` 填写为你的 Claude API 密钥，并在扩展设置中确认其他选项。

## 代码提交与备份建议

1. 初始化 git 仓库：

```powershell
git init
```

2. 添加所有文件并提交：

```powershell
git add .
git commit -m "Initialize project and add Claude Code configuration"
```

3. 如果需要备份到远程仓库，请添加远程地址并推送：

```powershell
git remote add origin <your-repo-url>
git push -u origin main
```

## 维护建议

- 定期备份 `region_db.json` 和生成的结果文件
- 将业务逻辑与界面逻辑分离，便于后续扩展
- 如果需要进一步增强 Claude Code 集成，可考虑添加自定义任务、自动化脚本和提示模版
