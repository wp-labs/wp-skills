# WPL/OML 可复现生成约定

## 目标

对相同原始样本、相同的可选来源文档和相同 rule，重复生成的 WPL 与 OML 文件必须逐字节相同。规则文件是交付物；解析事件中的 `ingest_time` 和 `parse_time` 是运行时值，不用于比较生成确定性。

## 已有规则

如果目标仓库已有规则，仓库文件是唯一基准：

```text
models/wpl/<package>/parse.wpl
models/oml/<package>/<rule>/adm.oml
```

用户要求与现有 rule 一致时，先读取这两个文件并保留字段顺序、规则顺序、空格、注释和换行。将待交付候选文件分别与基准文件比较；`cmp` 必须返回 0。不得为了“格式统一”重写原文件。

字节一致只证明候选与基准相同，不代表基准符合当前规范。package 门禁失败时，报告一致性结果和具体失败项；未经用户要求，不擅自改写权威基准或声称验证通过。

```bash
cmp --silent /tmp/run-1/parse.wpl /tmp/run-2/parse.wpl
cmp --silent /tmp/run-1/adm.oml /tmp/run-2/adm.oml
cmp --silent /tmp/run-1/parse.wpl models/wpl/<package>/parse.wpl
cmp --silent /tmp/run-1/adm.oml models/oml/<package>/<rule>/adm.oml
shasum -a 256 models/wpl/<package>/parse.wpl models/oml/<package>/<rule>/adm.oml
```

比较失败时检查第一个差异：

```bash
diff -u /tmp/run-1/parse.wpl /tmp/run-2/parse.wpl
diff -u /tmp/run-1/adm.oml /tmp/run-2/adm.oml
```

如基准文件与当前规范冲突，报告差异和文件路径；不得自行更改基准后再宣称一致。

## 新规则

- 用户提供来源文档时按文档字段定义顺序生成；没有文档或文档未定义顺序时采用样本 JSON 键顺序。
- `parse.wpl` 中规则沿用 package 现有次序；全新 package 有来源文档时按文档日志类型顺序，没有文档时按用户样本首次出现的顺序。
- OML 按 skill 的固定顺序生成：归一化、业务时间、富化、标准行为信封、兼容投影、私有字段。
- 不写入生成日期、随机 ID、临时路径或依赖文件系统遍历次序的内容。
- 独立生成两次并对候选文件执行 `cmp`；通过后再运行 package 门禁。

## 样例基准

`360_active_defense_log` 的回归输入是 `models/wpl/360/sample.dat` 第一行。它包含中文、符号、空字符串和整数；比较样例时保留原始行，不重新序列化 JSON。权威输出是 `models/wpl/360/parse.wpl` 和 `models/oml/360/360_active_defense_log/adm.oml`，该 package 的其他日志 rule 也位于同一 WPL 文件中。

确定性检查验证模型文件字节，不要求不同 batch 的完整事件 JSON 相同，因为 `Now::time()` 按规范产生运行时 `ingest_time`、`parse_time`。
