# Clash

为SubConverter转换不同代理工具的订阅文件格式提供自定义配置

本仓库使用的SubConverter镜像：asdlokj1qpi23/subconverter，Github仓库地址：https://github.com/asdlokj1qpi233/subconverter

asdlokj1qpi23/subconverter forked from tindy2013/subconverter，区别是asdlokj1qpi23/subconverter支持Surge 5和Singbox的解析


## 国内分流与独立兜底

所有 INI 使用相同分工：

1. 广告／屏蔽规则。
2. 国内纯域名规则 → `➡️ 国内`（默认 `DIRECT`）。
3. 原有服务及 IP 分流规则。
4. `GEOIP,CN,no-resolve` → `➡️ 国内`，仅补充匹配已有真实目标 IP。
5. `FINAL` → `🐟 漏网之鱼`（默认 `港台日新韩-自动`，也可手动选择 `DIRECT`）。

国内域名规则在需要解析的 IP 规则前面；服务规则之后、FINAL 之前增加 `ruleset=➡️ 国内,[]GEOIP,CN,no-resolve`。直接使用真实 IP 或前面的规则已经取得真实 IP 时，才按 GeoIP 数据库进行国内补充匹配；只有域名且尚无真实 IP 时，不为这条规则主动解析，继续进入漏网之鱼。此规则不会撤销前面的规则已经触发的解析，也不保证数据库完整。兜底组只处理未命中的连接，不覆盖已经命中的服务规则。

| 配置文件 | 国内域名集合 | 目标 |
| --- | --- | --- |
| `Clash_wrt.ini`、`Clash_wrt_cdn.ini`、`Clash_fn.ini` | 内联 `GEOSITE,cn` | Mihomo；需要 geosite.dat，启用 GeoSite 自动更新 |
| `Clash.ini`、`Template.ini`、`Clash_qx.ini` | blackmatrix7 China_Domain.yaml（clash-domain） | 兼容普通 Clash／Quantumult X；订阅重新转换时更新规则 |

普通 Clash 和 Quantumult X 不使用 Mihomo 的 `GEOSITE` 指令；两类国内集合覆盖范围不完全相同。纯域名源不包含会提前触发解析的 IP 规则。`86400` 是 subconverter 的规则源刷新设置，不等于客户端自动更新订阅。

## OpenClash DNS 配套设置

仓库的 `openclash` 是 UCI 配置备份，不是 Mihomo YAML，也不会自动修改正在运行的路由器。这里只同步 DNS 相关项，其余配置保留。不要将整个备份盲目覆盖到不同路由器；可以按下面内容在面板逐项设置。

- 关闭“追加上游 DNS”，保留“自定义上游 DNS”，不启用 respect-rules。
- Cloudflare 的 `NameServer` 使用 HTTPS，地址 `1.1.1.1/dns-query`，指定 `港台日新韩-自动`，不勾选节点／直连域名解析。
- 两个运营商 DNS 放在 `Default-NameServer`，UDP，勾选节点域名解析和直连域名解析，不加入普通 `NameServer`。
- 在 OpenClash 面板启用 Nameserver-Policy，手动填写下面 `nameserver-policy` 下的 `"geosite:cn"` 映射，不包含 `dns:` 或 `nameserver-policy:` 外层。仓库不再提供单独的 DNS 策略文件；更新订阅不会自动应用这项面板设置。

最终 DNS 分工：

```yaml
dns:
  nameserver:
    - "https://1.1.1.1/dns-query#港台日新韩-自动"
  nameserver-policy:
    "geosite:cn":
      - "https://223.5.5.5/dns-query#➡️ 国内"
      - "https://223.6.6.6/dns-query#➡️ 国内"
  default-nameserver:
    - 202.102.224.68
    - 202.102.227.68
  proxy-server-nameserver:
    - 202.102.224.68
    - 202.102.227.68
  direct-nameserver:
    - 202.102.224.68
    - 202.102.227.68
```

上面是需要合并的 DNS 字段，保留实际配置的监听端口、Fake-IP 和 IPv6 设置，不是完整订阅。

上面的阿里 DoH 策略显式指定 `➡️ 国内`：组选择 DIRECT 时在本地查询，切为代理时查询也经过代理。阿里作为解析服务商仍能看到这些查询；节点／引导查询仍允许运营商 DNS 明文直连。

如果优先使用实测更快的运营商 DNS，并接受国内域名查询交给运营商，面板中的 Nameserver-Policy 也可以改为：

```yaml
"geosite:cn": ["202.102.224.68", "202.102.227.68"]
```

上述两种策略二选一。直接填写运营商 IP 的方案在当前 respect-rules: false 下不跟随国内组切换：即使把国内组切为代理，这些 DNS 查询仍直连。没有命中任何 DNS 策略的域名继续使用普通代理 Cloudflare nameserver。

`direct-nameserver` 处理最终选择 DIRECT 后的出口解析。对于正常获得 Fake-IP、随后提前命中国内直连规则的连接，可以只使用 direct-nameserver 完成目标解析，不必再配置 nameserver-policy。新增 GEOIP 的 no-resolve 只控制这一条规则，不能让客户端的真实 DNS 查询或其他 IP 规则免于解析。

此处保留 nameserver-policy，目的是让国内集合中的非 Fake-IP 查询也使用国内 DNS，例如被 fake-ip-filter 排除的域名、redir-host 模式或其他需要上游回答的查询。若接受这些查询仍使用普通代理 nameserver，可以在面板取消该策略；这属于简化配置与解析速度的取舍，并非 no-resolve 自动替代了策略。

IPv6 注意：按当前 Mihomo 实现，对未被过滤的普通 Fake-IP 域名，缺少 IPv6 Fake-IP 地址池时 AAAA 返回空答案，而不是必然改查真实 IPv6。被 fake-ip-filter 排除的域名走真实解析流程，是否返回 AAAA 还受 dns.ipv6 控制。因此不能仅凭“IPv6 Fake-IP 停用”判断是否需要 nameserver-policy；应核对实际内核和最终 fake-ip-filter。开启大陆绕过时，OpenClash 还可能把国内集合加入真实解析的过滤规则。

不配置 nameserver-policy 时，这些需要真实解析的查询仍走经过代理的 Cloudflare；保留策略则匹配国内集合后使用所选的阿里 DoH 或运营商 DNS。运营商 direct-nameserver 默认不遵循 nameserver-policy；不要误认为只要配置国内 DoH，直连出口就不会使用运营商 DNS。

### 优先级及切换注意事项

- 国内集合中的域名优先进入 `➡️ 国内`，可能覆盖后面的 SteamCN、Apple Music 等服务组。需要强制使用专用组的域名，应放在国内规则之前，并给同一域名添加 DNS 策略例外；不要简单把含有会触发解析的 IP 规则的整个服务列表移到前面。
- 国内组或兜底组切为代理，只影响真正进入 Mihomo 的流量。启用了 OpenClash“绕过中国大陆 IPv6”时，部分大陆 IPv6 连接可能在进入内核前就被放行；要让组切换对它们生效，需要同时调整 IPv6 绕过设置。仓库不自动更改此开关。
- Quantumult X 的 DNS 配置由该客户端另行管理；同步 INI 分组不代表它自动应用 OpenClash 的 DNS 策略。
- 转换后确认存在 `GEOSITE,cn,➡️ 国内`（Mihomo 模板），并以 `GEOIP,CN,➡️ 国内,no-resolve` 和 `MATCH,🐟 漏网之鱼` 结尾；普通 Clash 模板应展开国内域名规则，不能出现 GEOSITE。Quantumult X 使用其对应的 GEOIP / FINAL 语法，由 subconverter 转换。
- 更新路由器时先转换订阅，再应用配套 DNS 设置，确认策略组名完全一致。本文未声称已在实际路由器上做过性能或泄露测试。

## 本地检查

```sh
python -m unittest discover -s tests -v
```

检查规则顺序、组引用、客户端兼容性，以及 UCI 备份中的 DNS 上游分工。该检查不访问订阅、不连接真实节点，不能替代实际转换和 Mihomo 运行验证。
