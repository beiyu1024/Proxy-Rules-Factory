# Proxy-Rules-Factory

自动化、零冲突、每日同步社区最新共建源的分流规则与模板工厂，专为 **OpenClash / Mihomo / Subconverter** 设计。

## 核心特性

- **每天自动同步社区最活跃规则源**：通过 GitHub Actions 每天北京时间 `04:00` 自动拉取 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)（整合 `v2fly/domain-list-community` + `Loyalsoldier` + 社区实时 PR）及精选规则，永不过时。
- **全局跨组冲突仲裁**：按严格“私有 → 强拦截/细分专项(AI/OTA/GV/YouTube) → 流媒体/高频应用 → 大型生态父域(Google/Apple/Microsoft) → 国内外大盘”优先级清洗，彻底消灭**父域杀子域**、重复规则与死规则。
- **严控单文件体积（< 500 KB）**：国内大盘改由 `GEOIP,CN` + Mihomo `GEOSITE,cn` / `.mrs` 承担，彻底告别超限被 subconverter 静默丢弃的问题。
- **防测速风暴 & 防空组退化**：`url-test` / `fallback` 统一采用 `300s / 50ms` 合理参数并排除机场公告/流量假节点；业务组默认项绝不绑死可能为空的地区组；基础 `DIRECT` 组绝不参与测速。

## 产物说明

每次自动构建会产出三份核心文件：

1. **Subconverter 订阅转换模板（开箱即用）**
   ```
   https://raw.githubusercontent.com/beiyu1024/Proxy-Rules-Factory/main/dist/Beiyu_Pro.ini
   ```
   直接替换订阅转换链接中的 `config=` 参数即可（建议 URL 编码）。

2. **Mihomo 原生 `.mrs` 二进制规则集模板（极客热更新版）**
   ```
   https://raw.githubusercontent.com/beiyu1024/Proxy-Rules-Factory/main/dist/mihomo_mrs.yaml
   ```
   客户端每 24 小时自动热更新社区 `.mrs` 规则与本仓库私有规则，无需重新转换订阅。

3. **透明审计报告**
   - 查看 [`dist/AUDIT.md`](./dist/AUDIT.md) 了解每次构建的规则数量、文件体积及自动清理的冲突明细。

## 如何添加个人自定义规则

只需编辑 [`config/custom_overrides.yaml`](./config/custom_overrides.yaml) 并提交，GitHub Actions 会自动重新构建并生成最新模板。
