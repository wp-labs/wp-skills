# WPL 编写入口

当问题从“工程怎么做”进入“这条日志怎么写规则”时，看这个文件。

这里不重复整套 WPL 语言细节，只负责正确路由。

## 什么时候切到 WPL 编写流程

一旦用户的问题变成以下任意一种，就切到独立的 `wpl-rule-check` skill；如果当前环境未安装，则参考 `https://github.com/wp-labs/wpl-check`：

- 写新的 `rule.wpl` 或 `parse.wpl`
- 根据样本修规则
- 选择用单规则、包规则还是表达式
- 跑离线验证
- 调整字段命名、分组结构、样本组织方式

## 编写前先准备什么

至少准备：

- 代表性原始日志样本
- 目标字段
- 当前失败信息
- 当前规则文件或最小片段

如果是在 WP 工程里，优先按文档约定组织：

- `models/wpl/<name>/sample.dat`
- `models/wpl/<name>/parse.wpl`

如果是在 `wpl-check` 工作流里，优先按本仓库约定组织：

- `rule.wpl`
- `sample.txt`

## 首选学习入口

中文文档优先看：

1. `docs-zh/10-user/03-wpl/01-quickstart.md`
2. `docs-zh/10-user/03-wpl/01-wpl_basics.md`
3. `docs-zh/10-user/03-wpl/03-practical-guide.md`

配套工具入口：

- WpEditor / editor.warpparse.ai

## 进入可验证流程时怎么做

进入具体写规则阶段后，以 `wpl-rule-check` skill 或 `wpl-check` 仓库为主，因为它提供：

- 样本优先的工作流
- `wpl-check syntax`
- `wpl-check sample`
- 可直接复用的示例目录

## 差异处理原则

官方文档是学习入口，`wpl-check` 工具链是验证入口。

如果你发现：

- 文档写法和本地 grammar 看起来不一致
- 文档示例能表达思路，但本地校验不过

那么：

1. 以本地 `wpl-check` 可验证结果为准
2. 保留文档路径作为学习参考
3. 不要在上层 skill 里自行扩展语法解释
