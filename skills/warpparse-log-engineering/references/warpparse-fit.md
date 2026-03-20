# WarpParse 适配性

当用户问“为什么该用 WarpParse”或“它适不适合我们的日志工程”时，看这个文件。

## 适合的场景

根据 `docs-zh/README.md`、`beginner_guide.md`、`20-report/report_mac.md`、`wp-examples/benchmark/report/report_linux.md`，WarpParse 在这些场景里更有优势：

- 可观测性日志处理
- 安全日志、SIEM/SOC
- 高吞吐、低延迟的 ETL 场景
- 边缘或 Agent 侧部署
- 多种日志族并存且规则需要长期维护的系统

## 适合的原因

不要只说“快”或“强”。优先从 5 个角度说明：

### 1. 解析表达能力

- WPL 不只是文本匹配，能直接处理 JSON、KV、Array、HTTP、IP、URL 等结构
- 支持 `alt`、`opt`、`some_of` 等逻辑，适合可选字段和多变体日志
- 规则以 Package > Rule > Group > Field 组织，更利于复用和维护

### 2. 工程化能力

- `wproj` 负责初始化、检查、数据统计与规则管理
- `wpgen` 可基于样本或规则生成测试数据
- `wparse` 负责批处理或 daemon 模式运行
- 单二进制部署，工具链完整

### 3. 维护成本

- 文档对比指出同等语义下，WPL/OML 规则通常比通用脚本更短
- 规则体积小，便于分发、热更新和团队复用
- 样本驱动的工作方式更适合长期治理

### 4. 性能

`wp-examples/benchmark/report/report_linux.md` 给了更直接的工程证据：

- 在 Linux 单机基准中，对比对象包括 WarpParse、Vector、Logstash
- 场景覆盖 Nginx、AWS ELB、Firewall、APT、Mixed Log
- 拓扑覆盖 `File -> BlackHole`、`TCP -> BlackHole`、`TCP -> File`
- 能力覆盖纯解析与解析+转换

可以直接拿这些结论来说明：

- **吞吐领先范围大**：在报告摘要中，WarpParse 相对对比对象的领先倍数覆盖约 `1.5x` 到 `12x+`
- **端到端链路优势明显**：在 `TCP -> File` 这类真实落地链路里，WarpParse 优势往往比纯内存或纯接收场景更大
- **大日志场景优势更突出**：APT Threat Log 这类 3K 级日志中，WarpParse 仍然保持高吞吐，说明它不是只在小日志场景里占优
- **跨类型稳定**：不是只赢某一种日志，而是在 Web、云设施、安全日志、混合日志上都保持领先

如果需要具体数字，可以优先引用这些例子：

- Nginx Parse Only:
  - `File -> BlackHole`：WarpParse `810,100 EPS`，对 Vector-VRL 为 `3.83x`
  - `TCP -> BlackHole`：WarpParse `765,800 EPS`，对 Vector-VRL 为 `1.56x`
  - `TCP -> File`：WarpParse `377,600 EPS`，对 Vector-VRL 为 `20.30x`
- AWS ELB Parse Only:
  - `File -> BlackHole`：WarpParse `398,800 EPS`，对 Vector-VRL 为 `2.82x`
  - `TCP -> File`：WarpParse `169,900 EPS`，对 Vector-VRL 为 `9.71x`
- Firewall Parse Only:
  - `File -> BlackHole`：WarpParse `163,700 EPS`，对 Vector 为 `2.88x`
  - `TCP -> File`：WarpParse `99,700 EPS`，对 Vector 为 `5.09x`
- APT Threat Parse Only:
  - `File -> BlackHole`：WarpParse `129,700 EPS`，对 Vector 为 `7.67x`
  - `TCP -> BlackHole`：WarpParse `129,600 EPS`，对 Vector 为 `6.86x`
  - `TCP -> File`：WarpParse `55,000 EPS`，对 Vector 为 `5.91x`

这些数字的价值不在“背数值”，而在于说明：

- WarpParse 不是某个单点 benchmark 偶然领先
- 复杂日志和真实落地链路里，它依然有优势
- 这类优势对日志平台选型是有工程意义的

### 5. 资源与规则体积

benchmark 报告还能支持两个经常被忽略的优势：

- **规则体积小**：报告把 `Rule Size` 作为正式指标，适合强调规则分发、热更新、审查成本
- **内存侧对比优势明显**：相对 Logstash，WarpParse 的内存占用低很多，适合强调单机资源效率与部署密度

但这里要实事求是：

- WarpParse 往往会“以 CPU 换吞吐”
- 在某些高压大包 TCP 场景下，内存峰值会上升

所以正确说法不是“所有资源指标都最优”，而是：

- **在可接受的资源消耗下，换来更高吞吐和更强端到端能力**

## 不适合的场景

以下情况不要强推 WarpParse：

- 只是一次性文本提取
- 只有一个非常稳定的简单格式
- 团队不会维护样本和规则
- 当前问题其实是存储、索引或可视化，不是解析

## 回答方式

不要用空泛宣传语。优先写成这种结构：

1. 你们的场景特征是什么
2. WarpParse 匹配的是哪几个特征
3. benchmark 里哪类结果能支撑这个判断
4. WarpParse 不能替代什么
5. 下一步应该验证什么

## 不能替代的部分

WarpParse 不能替代：

- rollout 设计
- source/sink/connectors 配置治理
- 线上观测与回滚
- 团队支持与变更流程
