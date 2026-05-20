# GameBot

本地离线运行的 PC 游戏自动化工具原型。它通过可视化界面管理任务和图片规则，按间隔截图，用 OpenCV 模板匹配找图，命中后执行点击、等待、按键或拖拽。

> 请只在允许自动化的单机游戏、测试环境或你有权限的场景中使用。在线游戏可能禁止自动化工具。

## 快速开始

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m gamebot.main
```

## 当前能力

- 三栏 PyQt6 桌面界面：任务列表、任务编辑、运行日志。
- 项目 JSON 导入 / 导出。
- 任务按列表顺序串行调度：一次只执行一个任务，A 执行完后再判断 B 是否到达触发条件。
- 任务启用 / 禁用、连续未匹配自动暂停。
- OpenCV `matchTemplate` 模板匹配，支持 ROI、多实例匹配、阈值。
- 动作执行：点击、双击、右键、等待、按键、拖拽。
- 全局停止 / 暂停热键配置入口，Windows 下尝试注册。

## 配置位置

- 示例配置：[config/sample_project.json](config/sample_project.json)
- 默认保存目录：`config/`
- 日志目录：`logs/`

## 注意

不同游戏的窗口捕获方式差异很大。这个版本优先使用全屏截图加 ROI 匹配，窗口标题主要用于运行前状态检查和日志提示；如果某些游戏使用独占全屏或反作弊保护，截图与输入控制可能被系统或游戏拦截。
