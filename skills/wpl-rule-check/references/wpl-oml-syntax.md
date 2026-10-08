# WPL/OML 实作速查（新标准）

## WPL

```wpl
#[tag(log_desc: "产品事件", log_type: "event_log")]
package vendor {
  rule event_log {
    (json(time@event_time, ip@src_ip, ip@dst_ip, chars@action))
  }
}
```

- `chars`：文本；`digit`：整数；`time`/`time_timestamp`：时间；`ip`：地址；`array`：数组。
- 有用户提供的原始文档时，JSON/KV 只提取文档定义的字段；没有字段说明时，按样本实际字段生成，并从字段名、JSON 类型和值推断 WPL 类型。明确的时间、IP、端口和数组必须使用对应类型。
- 一种格式一个稳定 rule；有文档时按明确的标识和值路由。无文档时依据样本中稳定的 `log_type` 或现有规则推断并标注；不要加入没有样本证据的字段存在性、`dev_id`、`index` 或猜测性的 `f_has/f_not_has`。
- `@name` 是字段捕获名，OML 只能读取已捕获字段。字段遗漏先修 WPL，不在 OML 中读取不存在的字段。
- 每个业务 rule 保留独立 raw 旁路：`copy_event_parse(rule: "raw_log/raw_log")`；不修改明确的 ignore 规则。

## OML 固定结构

```oml
name : <log_type>
rule : <package>/<rule>
---
__now = Now::time();
// 1. 归一化、结果和对象身份临时值
// 2. 业务时间 -> Time::to_ts_zone(8, ms)
// 3. 四类 IP 富化
// 4. meta / behavior / subject / object / carriers / observation / extensions
```

### 常用表达式

```oml
__ip: ip = read(src_ip);
__name = pipe read(file_path) | path(name);
__action = match read(action) {
    chars(block) => chars(block);
    chars(allow) => chars(allow);
    _ => chars(unknown);
};
__occur_time = pipe read(event_time) | Time::to_ts_zone(8, ms);
```

标准对象、富化和方向计算先写入唯一 `__` 临时变量，再复用它。下面四个顶层兼容字段直接读取 WPL 捕获的原始字段，不读取带 `ip` 类型的临时变量。普通字段直接 `read`，只有契约要求省略空值且有明确条件时才使用 `skip_empty`。

### 新行为信封投影

- `meta`：身份、时间、映射版本和 `data_source`。
- `behavior`：`layer/type/operation/outcome/message`；`outcome` 必须由来源动作/结果证据推导。
- `subject/object`：实体角色；实体未知为 `null`，不可用空对象。
- `carriers`：承载进程/脚本的引用数组，没有关系证据就为空数组；不得用主体/客体冒充载体。
- `facets`：领域行为细节；只使用 Schema 登记的 `network/process/file/authentication/http` 等领域键。
- `observation`：检测产品的 observer、动作、assertion 和 evidence refs。
- `extensions`：只保留无法标准化的私有字段、画像、富化和未知非空值。

兼容顶层保留 `attacker_entity`、`victim_entity`、`attacker_ip`、`victim_ip`、`occur_time`，但不输出顶层 `event_id`。检测事件中的攻击者和受害者使用标准对象及 `observation.assertion.attacker[]`、`observation.assertion.victim[]`。

前四个字段始终输出。逐条检查 WPL 捕获和 `__sip/__dip/__attacker_ip/__victim_ip` 的原始读取来源，再按本条日志实际可用的字段选择：`attacker_entity` 为攻击者 IP、攻击者 host、源 IP、源 host、空字符串；`victim_entity` 为受害者 IP、受害者 host、目的 IP、目的 host、空字符串；`attacker_ip` 为攻击者 IP、源 IP、空字符串；`victim_ip` 为受害者 IP、目的 IP、空字符串。来源字段名因产品而异，不固定写成 `src_ip/dest_ip`。每级使用 `match read(原始字段) { is_empty() => 下一级或 chars(""); _ => read(原始字段); }`，保证空字符串兜底；不要从已转换的 `__` IP 值回填这四个兼容字段。

### 四类 IP 富化

只对原始字段语义明确的通信或攻防 IP 查询 GeoIP。查询参数使用 `ip_to_biguint` 或 `ip4_to_int`。GeoIP 写入对应实体 endpoint/host 的 `geo`，可包含 `continent_name` 与 `country_code`，无值时省略且禁止空对象；官网当前没有 `endpoint.resource`，资产编号、名称、类型分别写入 `endpoint.asset_id`、`endpoint.asset_name`、`endpoint.asset_type`，其余资产结果按语义平铺到 `endpoint.system.{id,name}` 或 `endpoint.organization.{id,name}`。`endpoint.asset_id` 不参与 `ref_id`，`asset_name` 不等同于 `host.name`，`asset_type` 按需归一到 `device.type` 或 `resource.kind`。四类 IP 及其 GeoIP/资产不得复用到 carriers。通信方向写 `facets.network.direction`，攻击方向写 `observation.assertion.attack_direction`。

### 来源告警

告警标题、严重度、规则、处置动作和检测结论进入 `observation.assertion`。来源 action 保留原文；有用户文档时按其结果枚举推导 outcome。没有文档时根据字段名、值域和记录上下文推断并标注；没有足够结果证据时使用 `unknown` 或报告 `NEEDS_INPUT`，不能用产品名、标题或 severity 代替结果。
