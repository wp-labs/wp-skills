## 使用 wp-skills，玩转 WarpParse!

第一次接触 WarpParse，会经常遇到一些问题：

- 配置文件这么多，先改哪个？
- `source`、`sink`、`connectors`、`models`、`topology` 是什么关系？
- `wpgen`、`wp-monitor` 又是干嘛的？

其实，难的不是 WarpParse 本身，而是第一次上手时，会被工程结构吓住。

`wp-skills` 就是为了解决这个问题而生的。它是一套专门给 WarpParse 准备的 AI 技能包，能让 AI 助手直接帮你做配置、写规则、查问题、理清链路。

对新手最有帮助的，主要是两个 skill：

- `wp-deploy`：负责部署和接线配置。
- `wpl-rule-check`：负责规则编写和验证。

它们的分工非常清楚。

`wp-deploy` 解决的是“怎么跑起来”的问题，比如：

- 怎么配 `source`
- 怎么配 `sink`
- `connectors` 和 `topology` 怎么接
- `conf/wparse.toml` 怎么写
- `wpgen` 怎么灌测试流量
- `wp-monitor` 怎么接观测
- 怎么组织一套可运行的联调或部署配置

`wpl-rule-check` 解决的是“规则怎么写对”的问题，比如：

- 一条日志该怎么解析
- `parse.wpl` 怎么写
- `.oml` 怎么写
- 为什么规则匹配不上
- 怎么用 `wpl-check` 验证

## 安装

```bash
git clone https://github.com/wp-labs/wp-skills.git
cd wp-skills
install-skill.sh wp-deploy
install-skill.sh wpl-rule-check
```

装好之后，你就可以直接让 AI 帮你做事，比如：

- “帮我配一个 file source，把样本跑进 WarpParse”
- “帮我加一个 file sink，把结果输出成 JSON”
- “帮我接一个 wpgen，往 tcp source 发测试数据”
- “帮我接 wp-monitor，看 parse 和 miss 指标”
- “这条日志帮我写 WPL 和 OML，并验证一下”

对于新手来说，先别急着死啃文档，  
先装上 `wp-skills`，  
让 `wp-deploy` 带你把链路跑起来，  
再让 `wpl-rule-check` 带你把规则写对。

最推荐的入门顺序是：

1. 先跑一个最简单的 `file source -> file sink` 示例
2. 再用 `wpl-rule-check` 写规则并验证
3. 然后加上 `wpgen` 做联调
4. 最后接 `wp-monitor` 看整条链路状态

这样，你不是在“硬学 WarpParse”，  
而是在“用起来的过程中学会 WarpParse”。