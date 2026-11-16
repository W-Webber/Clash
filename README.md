# Clash

为SubConverter转换不同代理工具的订阅文件格式提供自定义配置

本仓库使用的SubConverter镜像：asdlokj1qpi23/subconverter，Github仓库地址：https://github.com/asdlokj1qpi233/subconverter

asdlokj1qpi23/subconverter forked from tindy2013/subconverter，区别是asdlokj1qpi23/subconverter支持Surge 5和Singbox的解析


## 国内分流与独立兜底

所有 INI 使用相同分工：

1. 广告／屏蔽规则。
2. 国内纯域名规则 → `➡️ 国内`（默认 `DIRECT`）。
3. 原有服务及 IP 分流规则。
4. `FINAL` → `🐟 漏网之鱼`（默认 `港台日新韩-自动`，也可手动选择 `DIRECT`）。

国内规则在需要解析的 IP 规则前面；未被国内集合覆盖的域名仍会经过后续 IP 匹配，不能保证完全消除这部分解析延迟。兜底组只处理未命中的连接，不覆盖已经命中的服务规则。

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

国内 DNS 使用阿里 DoH 并显式指定 `➡️ 国内`：组选择 DIRECT 时在本地查询，切为代理时查询也经过代理。不要将这个策略改成固定直连的运营商 DNS 后，再把国内组切到代理，否则国内域名查询仍会直连。阿里作为解析服务商仍能看到这些查询；节点／引导查询仍允许运营商 DNS 明文直连。

`direct-nameserver` 仅处理最终选择 DIRECT 的出口解析；即使国内域名提前匹配，它也不能替代连接前 AAAA 查询使用的 nameserver-policy。未知域名和用于 IP 判断的普通解析仍使用 Cloudflare 代理 DNS。

### 优先级及切换注意事项

- 国内集合中的域名优先进入 `➡️ 国内`，可能覆盖后面的 SteamCN、Apple Music 等服务组。需要强制使用专用组的域名，应放在国内规则之前，并给同一域名添加 DNS 策略例外；不要简单把含有会触发解析的 IP 规则的整个服务列表移到前面。
- 国内组或兜底组切为代理，只影响真正进入 Mihomo 的流量。启用了 OpenClash“绕过中国大陆 IPv6”时，部分大陆 IPv6 连接可能在进入内核前就被放行；要让组切换对它们生效，需要同时调整 IPv6 绕过设置。仓库不自动更改此开关。
- Quantumult X 的 DNS 配置由该客户端另行管理；同步 INI 分组不代表它自动应用 OpenClash 的 DNS 策略。
- 转换后确认存在 `GEOSITE,cn,➡️ 国内`（Mihomo 模板）及末尾 `MATCH,🐟 漏网之鱼`；普通模板应展开为域名规则，不能出现 GEOSITE。
- 更新路由器时先转换订阅，再应用配套 DNS 设置，确认策略组名完全一致。本文未声称已在实际路由器上做过性能或泄露测试。

## 本地检查

```sh
python -m unittest discover -s tests -v
```

检查规则顺序、组引用、客户端兼容性，以及 UCI 备份中的 DNS 上游分工。该检查不访问订阅、不连接真实节点，不能替代实际转换和 Mihomo 运行验证。
