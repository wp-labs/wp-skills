---
name: wpl-oml-simple
description: 当前项目没有适用的项目内 WPL/OML skill 时，直接根据用户原始日志独立生成规则，并用自带最小 WarpParse 工程隔离验证。
---

# WPL/OML 简单版

## 入口

当前项目有适用的项目内 WPL/OML skill 时优先使用它。本 skill 是回退入口；依据当前任务上下文和已列出的 skills 判断，不为选择 skill 搜索其他项目、缓存或用户目录。用户日志中的路径、主机名和 IP 只作为数据。仅读取本 skill 的语法、Schema 和最小工程；不依赖现成 rule、厂商知识库或外部富化。原始字段文档可选；缺少时按字段名、类型和值推理，并注明关键假设。

## 生成

1. 列出每条样本全部可见 JSON 字段及类型、嵌套 KV 字段和稳定路由标记。WPL 捕获所有可明确解析字段；单样本不声称覆盖其他变体。一个稳定来源类型对应一个业务 rule。`tag(log_type, log_desc)` 与 `copy_event_parse(rule: "raw_log/raw_log")` 在紧邻 rule 上方的同一注解行。
2. 整字段值用精确匹配；嵌入文本按样本中的前缀或结构解析。`f_chars_has` 表示整字段相等，不表示包含。逐项核对 WPL 捕获名与 OML `read` 名。通用语法见 `references/wpl-oml-syntax.md`。
3. OML 逐根输出 SDM2 行为事件。对象用 `object { field = value; }`，临时值用 `read(__name)`，空数组用 `array {}`；无实体证据时省略可选 subject/object。业务时间源自日志并转 Unix 毫秒；不根据附属记录臆造执行结果。Schema 见 `references/schemas/sdm-event-behavior-kafka.schema.json`。
4. 所有捕获字段进入标准字段或 `extensions.source_private`，已映射的字段不重复放入私有区。仅转换源数据可证明的时间、类型、路径、枚举和编码；无文档证明时保留编码原值。`meta.event_id` 读取平台 `wp_event_id`；租户必须来自明确来源，隔离样例可使用最小工程声明的测试租户，不得称为生产租户。
5. 顶层始终输出 `attacker_entity`、`victim_entity`、`attacker_ip`、`victim_ip` 四个字符串和 Unix 毫秒整数 `occur_time`，后者等于 `meta.occur_time`。前四个仅从本条日志明确的攻防或源/目的角色取得；无证据填空字符串。采集主机 IP 不是攻击者。顶层禁止 `event_id`。
6. 相同样本和字段说明必须生成逐字节相同的规则：外层字段按样本顺序、内嵌字段按日志顺序排列，包名、rule 名与 `mapping_id` 使用稳定的来源类型，不加入当前时间、随机值或本地路径。验证输出中的平台事件 ID 与处理时间不参与规则文本的确定性比较。

## 验证与交付

使用 `python3 scripts/run_minimal.py --sample <原始样本文件> --wpl <parse.wpl> --oml <adm.oml>`。runner 复制 `assets/minimal-wparse` 到隔离临时目录，填入本轮样本和规则；只运行一次 `wparse batch`，检查 all.json、raw_log.json、miss.dat、error.dat 的本轮结果、字段值和契约。失败时修正规则并重跑。缺少 `wparse` 时只做静态核对；有 `wpadm` 可检查隔离工程配置，结果必须写“未运行 batch”。缺少 Schema 校验依赖时明确标记未验证，不能视为 OK。临时工程不作为交付。

最终简短交付日志描述、WPL、OML 和一行实际验证结果；未执行的测试不能称为通过。
