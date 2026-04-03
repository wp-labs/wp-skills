# WPL/OML 编写入口与职责分工

当问题从”工程怎么做”进入”这条日志怎么写规则”时，看这个文件。

## 两个 skill 的职责分工

| 任务类型 | 使用哪个 skill |
|---------|--------------|
| 分析日志样本，编写 WPL 解析规则 | **wpl-rule-check** |
| 编写或修改 OML 富化模型 | **wpl-rule-check** |
| WPL/OML 语法问题 | **wpl-rule-check** |
| 调试规则匹配失败 | **wpl-rule-check** |
| WarpParse 是否适合评估 | **warpparse-log-engineering**（本 skill） |
| 工程目录初始化 (`wproj init`) | **warpparse-log-engineering**（本 skill） |
| 配置 source/sink/connector | **warpparse-log-engineering**（本 skill） |
| 部署和 rollout | **warpparse-log-engineering**（本 skill） |
| 规则写好后接入工程 | **warpparse-log-engineering**（本 skill） |
| 生产运维和故障排查 | **warpparse-log-engineering**（本 skill） |

## 两个 skill 的协作流程

```
用户场景：接入一种新的日志
          ↓
1. [warpparse-log-engineering] 评估是否适合用 WarpParse
2. [warpparse-log-engineering] 初始化工程目录 (wproj init)
3. [warpparse-log-engineering] 配置 source/sink/connector
          ↓
4. [wpl-rule-check] 分析日志样本
5. [wpl-rule-check] 编写 WPL 解析规则 (parse.wpl)
6. [wpl-rule-check] 编写 OML 富化模型 (.oml)
7. [wpl-rule-check] 通过 wpl-check 验证规则
          ↓
8. [warpparse-log-engineering] 集成到工程，运行 wparse batch 验证
9. [warpparse-log-engineering] rollout 到生产
10. [warpparse-log-engineering] 监控和运维
```

## ⛔ 强制路由触发条件

**一旦出现以下任一情况，必须立即切换到 `wpl-rule-check` skill：**

| 触发条件 | 动作 |
|----------|------|
| 用户提供样本数据要求解析 | 立即切换 |
| 用户要求写新的 `rule.wpl` 或 `parse.wpl` | 立即切换 |
| 用户要求编写 OML 富化模型 | 立即切换 |
| 用户要求修改现有规则 | 立即切换 |
| 用户询问 WPL/OML 语法或”怎么写” | 立即切换 |
| 需要验证规则是否正确 | 立即切换 |
| 讨论字段命名、分组结构 | 立即切换 |

**切换声明：**
```
此任务已进入 WPL 规则编写阶段，切换到 wpl-rule-check skill。
```

如果当前环境未安装 `wpl-rule-check`：
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) wpl-rule-check
```

或参考 `https://github.com/wp-labs/wpl-check`。

## 🚫 在本 skill 中的禁止行为

1. ❌ 直接编写 WPL 规则代码
2. ❌ 直接编写 OML 富化模型
3. ❌ 猜测或试错 WPL/OML 语法
4. ❌ 跳过 `wpl-rule-check` 的工作流程

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

### wpl-check 常用命令

```bash
# 语法检查（自动检测模式）
wpl-check syntax path/to/rule.wpl

# 样本解析（默认使用 rule.wpl + sample.txt）
wpl-check sample ./demo_dir

# 内联样本快速验证
wpl-check sample --data '{"key":"value"}' rule.wpl

# Package 多规则选择
wpl-check sample --package --rule-name rule_name rule.wpl sample.txt
```

## 差异处理原则

官方文档是学习入口，`wpl-check` 工具链是验证入口。

如果你发现：

- 文档写法和本地 grammar 看起来不一致
- 文档示例能表达思路，但本地校验不过

那么：

1. 以本地 `wpl-check` 可验证结果为准
2. 保留文档路径作为学习参考
3. 不要在上层 skill 里自行扩展语法解释
