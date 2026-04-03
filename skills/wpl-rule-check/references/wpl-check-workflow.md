# wpl-check 验证工作流

本文档介绍如何使用 `wpl-check` 工具离线验证 WPL 规则。

---

## 工具安装

```bash
# 从官方安装
bash <(curl -fsSL https://raw.githubusercontent.com/wp-labs/wp-skills/main/install-skill.sh) wpl-rule-check

# 或参考
# https://github.com/wp-labs/wpl-check
```

---

## 工程目录结构（最小集）

```
models/
  wpl/
    <package_name>/
      parse.wpl      # WPL 规则文件
      sample.dat     # 测试样本文件（每行一条日志）
  oml/
    <oml_name>.oml   # OML 富化模型文件
```

---

## 常用命令

### 语法检查

```bash
# 检查 WPL 语法
wpl-check syntax models/wpl/<package>/parse.wpl

# 检查 OML 语法（若工具支持）
wpl-check syntax models/oml/<name>.oml
```

### 样本测试

```bash
# 运行样本测试
wpl-check sample models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat

# 详细输出（显示解析结果和失败原因）
wpl-check sample --verbose models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat

# JSON 格式输出（方便程序处理）
wpl-check sample --json models/wpl/<package>/parse.wpl models/wpl/<package>/sample.dat
```

### 通过 wproj 工程集成验证

```bash
# 检查整个工程配置
wproj check

# 批处理模式验证（更接近生产环境）
wparse batch --stat 5 -p

# 查看解析统计
wproj data stat

# 查看未匹配的样本
ls data/miss.dat data/error.dat
```

---

## 验证工作流

```
1. 编写 WPL 规则
         ↓
2. wpl-check syntax   →  语法错误？修正
         ↓
3. 准备 sample.dat（3-5 条代表性样本）
         ↓
4. wpl-check sample   →  匹配失败？看报错定位字段
         ↓
5. 所有样本通过
         ↓
6. （可选）接入 wproj，运行 wparse batch 验证完整链路
```

---

## sample.dat 格式

- 每行一条完整的原始日志
- 不需要任何格式包装
- 建议覆盖多种变体（不同 type、可选字段有无等）

```
# sample.dat 示例（每行一条日志，这行注释实际不需要）
{"event_type":"login","src_ip":"1.2.3.4","port":22,"user":"admin","time":"2025-01-01 12:00:00"}
{"event_type":"logout","src_ip":"1.2.3.4","port":22,"user":"admin","time":"2025-01-01 12:01:00"}
{"event_type":"login","src_ip":"5.6.7.8","port":22,"user":"root","time":"2025-01-01 12:02:00"}
```

---

## 常见报错解读

| 报错信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `unexpected token at line N` | 语法错误，缺少分隔符或括号 | 检查分隔符写法，确认括号配对 |
| `field 'xxx' not found` | 字段没有命名或名字不匹配 | 检查 `:name` 命名 |
| `type mismatch for 'xxx'` | 字段类型不匹配 | 检查字段实际值是否符合类型 |
| `rule match failed` | 规则整体不匹配 | --verbose 查看在哪个字段失败 |
| `json parse error` | JSON 格式错误或有 BOM | 检查是否需要 `\| strip/bom \|` |
| `f_chars_has filter failed` | 过滤条件不匹配 | 检查目标字段的实际值 |

---

## 调试技巧

### 1. 隔离问题字段

把复杂规则拆成片段测试：

```wpl
// 先只测试 JSON 解析，不加过滤
rule debug_step1 {
  (json(chars@event_type, ip@src_ip))
}

// 解析通过后，加过滤
rule debug_step2 {
  (json(chars@event_type:type, ip@src_ip) | f_chars_has(type, login))
}
```

### 2. 检查 type 字段实际值

如果 `f_chars_has(type, login)` 失败，先去掉过滤看看字段实际提取的是什么值：

```wpl
// 去掉过滤条件，看 type 字段实际值
rule debug_no_filter {
  (json(chars@event_type:type, ip@src_ip))
}
```

用 `--verbose` 或 `--json` 查看输出，确认 type 字段的值。

### 3. Syslog 前缀字段数不确定

用 `*_` 替代固定数量的 `N*_`：

```wpl
// 如果不确定 syslog header 有几个字段
_:pri<<,>>,
*_,           // * 表示任意多个，直到能匹配后续内容
json(...)
```

---

## 与工程集成的注意事项

1. **wpl-check 通过 ≠ 工程路由成功**：wpl-check 只验证规则本身，还需要确认 source/sink 配置正确才能让数据流入规则
2. **sample.dat 的局限性**：单样本测试通过不代表覆盖了所有变体，生产验证用 `wparse batch` + `wproj data stat`
3. **miss.dat 和 error.dat**：`wparse batch` 后检查这两个文件，了解未匹配和解析错误的样本

如果需要接入工程，切换到 `warpparse-log-engineering` skill。
