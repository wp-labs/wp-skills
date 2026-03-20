# 支持、排障与升级

当用户问“遇到问题怎么查”、“怎么提支持请求”、“可以寻求什么帮助”时，看这个文件。

## 先区分问题类型

常见问题分 4 类：

1. 安装与环境问题
2. 工程目录、connectors、source/sink 配置问题
3. WPL 编写与样本解析问题
4. 方案适配或复杂日志接入问题

## 已确认的支持形式

根据 `docs-zh/10-user/09-FQA/user_suggestions_qa.md` 与 `https://github.com/wp-labs`，当前可以明确写出的支持形式有：

- 通过 **WpEditor** 降低编写和调试成本
- 通过 **AI + Skills** 自动生成或优化 WPL
- 对复杂日志提供官方解析支持，包括规则建议、示例、定位与优化
- GitHub 组织页提供公开入口：`https://github.com/wp-labs`
- 公开邮箱：`community@warpparse.ai`
- GitHub Discussions：适合提问、交流经验、讨论用法
- `wp-bugs` 仓库：适合提交可复现 bug
- 官方文档、在线编辑器、示例站点：适合作为自助支持入口

注意：当前我仍然没有看到一个明确写死的工单系统或 IM 群号。不要擅自编造更细的支持流程。

## 对外入口怎么选

优先按问题类型选择：

- 用法咨询、经验交流、非阻塞问题：GitHub Discussions
- 可复现缺陷、行为异常、版本回归：`wp-bugs`
- 需要社区联系或人工转接：`community@warpparse.ai`
- 文档学习、自助排查：`docs.warpparse.ai`
- 规则试写和交互式调试：`editor.warpparse.ai`

如果用户只给了一个模糊问题，不要直接把所有入口都丢给他。先帮他判断问题类型，再推荐单一主入口。

## 提支持前先收集这些材料

无论找谁支持，先准备：

- 已脱敏的原始样本
- 期望提取的字段
- 当前规则文件或关键片段
- 运行命令
- 完整报错或统计输出
- 当前目录结构或相关配置路径
- 最近改了什么

## 不同问题要附什么

### 安装与环境

- 安装方式：脚本、release 还是 Docker
- 系统信息
- 可执行文件是否在 PATH
- 失败命令与完整输出

### 工程与部署

- `wproj check` 输出
- `wproj data stat` 输出
- `conf/wparse.toml`
- connectors/source/sink 相关配置
- `data/logs/` 日志

### WPL 与解析

- 样本
- 规则文件
- 离线验证命令
- 失败定位信息

此类问题优先切到独立的 `wpl-rule-check` skill，或直接使用 `wpl-check` 离线验证流程。

### 方案与复杂接入

- 日志类型与规模
- 下游目标
- 是否已有现成 parser 或历史脚本
- 当前为什么觉得现有方案不够用

## 优先排障路径

推荐排查顺序：

1. `wproj check`
2. `wproj data stat`
3. 查看 `conf/wparse.toml`
4. 查看 source/sink/connectors 实际解析结果
5. 查看 `data/logs/`
6. 如果是规则问题，转离线 WPL 验证流程

## 回答风格

当用户说“如何寻求支持”时，不要只回答一句“联系官方”。

至少给出：

- 当前属于哪一类问题
- 先准备哪些材料
- 先跑哪些自查命令
- 如果需要升级支持，应该把哪几份文件和输出一起带上
- 最适合的公开入口是哪个：
  - `https://github.com/wp-labs`
  - `https://github.com/orgs/wp-labs/discussions`
  - `https://github.com/wp-labs/wp-bugs`
  - `community@warpparse.ai`
