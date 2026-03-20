---
name: warpparse-log-engineering
description: 面向大规模日志解析的 WarpParse 方案评估与工程落地。用于比较日志解析方案、判断 WarpParse 是否适合当前链路、规划 WP 工程初始化与部署 rollout、把具体 WPL 编写任务路由到正确工作流，以及整理有效的排障与支持材料。
triggers:
  - 日志解析方案选型或对比
  - WarpParse 适用性评估
  - 日志工程化部署规划
  - WPL 编写入口路由
  - 日志解析排障与支持
dependencies:
  optional:
    - wproj
    - wparse
    - wpgen
    - wpl-check
  docs:
    - docs.warpparse.ai
    - editor.warpparse.ai
    - https://github.com/wp-labs
---

# WarpParse 日志工程化

用这个 skill 处理“日志解析工程怎么做”，不要只盯着单条规则。

它覆盖 5 类问题：

1. 方案选择
2. 为什么适合用 WarpParse
3. WP 工程初始化、部署与 rollout
4. WPL 编写入口与学习路径
5. 如何排障、如何准备支持材料

当任务已经变成“针对样本写或修 `rule.wpl` / `parse.wpl`”时，切换到独立的 `wpl-rule-check` skill；如果当前环境没有该 skill，则参考 `https://github.com/wp-labs/wpl-check` 的验证流程。

## 工作方式

1. 先界定问题，而不是先给工具结论：
   - 日志种类有多少
   - 日志格式是否经常漂移
   - 目标字段是什么
   - 解析要跑在什么位置
   - 谁维护规则、谁承担线上责任
2. 再选当前轨道：
   - 方案选择：`references/solution-selection.md`
   - WarpParse 适配性与价值：`references/warpparse-fit.md`
   - WP 初始化、运行与 rollout：`references/wp-deployment.md`
   - WPL 编写入口：`references/wpl-authoring-routing.md`
   - 支持、排障与升级：`references/support-paths.md`
3. 输出必须落到一个具体结果：
   - 推荐方案
   - 推荐原因
   - 下一份要产出的工件

## 工程边界

- 把 `wproj`、`wpgen`、`wparse` 视为工程化落地工具链。
- 把 `wpl-check` 视为离线编写和验证 WPL 的本地工具，不等同于整个 WarpParse 部署。
- 如果用户只是在学 WPL 语法，不要在这里重复整套语言细节，转到独立的 `wpl-rule-check` skill 或 `wpl-check` 仓库。
- 如果官方文档示例与本地 `wpl-check` 验证行为有差异，以本地 `wpl-check` 可验证流程为准。
- 不要虚构未在文档或仓库里出现的部署命令、控制面能力、支持渠道。

## 最低输入要求

在给出可执行建议前，尽量拿到这些信息：

- 3 到 10 条代表性原始日志
- 期望提取的字段或目标 schema
- 当前或目标运行位置
- 当前任务属于评估、部署、编写、排障中的哪一类
- 是否已有现成 WP 工程目录

## 完成标准

结束前必须说明：

1. 这次解决的是哪一类问题。
2. WarpParse 在这里应该做什么，不应该做什么。
3. 下一步最具体的工件是什么：
   - `wproj init` 初始化后的工程目录
   - 可复现样本集
   - `rule.wpl` / `sample.txt`
   - rollout 检查清单
   - 支持请求材料包
