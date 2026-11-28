# Proxy-Rules-Factory 自动构建审计报告

- **构建时间**：`2026-11-28 02:31:04 UTC`
- **上游原始规则总量**：`138257` 条
- **清洗后输出规则总量**：`123029` 条（零重复、零冲突、零死规则、零超限截断）
- **自动清理统计**：组内冗余 `11516` 条 ｜ 跨组精确冲突 `3608` 条 ｜ 跨组父域遮蔽 `104` 条

## 各业务分组产出明细（按优先级从高到低）

| 优先级 | 策略组 | 文件 | 输出规则数 | 体积 | 组内去重 | 跨组冲突清理 | 父域遮蔽清理 |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | 🏠 局域服务 | `dist/rules/lan.list` | 152 | 4.9 KB | 125 | 0 | 0 |
| 2 | 🤓 私人服务 | `dist/rules/private_direct.list` | 7 | 0.3 KB | 0 | 0 | 0 |
| 3 | 🚁 动态直连 | `dist/rules/dynamic_direct.list` | 3 | 0.2 KB | 0 | 0 | 0 |
| 4 | 🚻 动态代理 | `dist/rules/dynamic_proxy.list` | 11 | 0.4 KB | 1 | 0 | 0 |
| 5 | ☎️ 国外-DNS | `dist/rules/foreign_dns.list` | 30 | 1.1 KB | 0 | 0 | 0 |
| 6 | 🛡️ 广告拦截 | `dist/rules/adblock.list` | 976 | 26.8 KB | 22 | 0 | 0 |
| 7 | ⬆️ 苹果升级 | `dist/rules/apple_ota.list` | 78 | 2.8 KB | 0 | 0 | 0 |
| 8 | 🤖 OpenAI | `dist/rules/ai_openai.list` | 43 | 1.5 KB | 16 | 0 | 0 |
| 9 | 🤖 Gemini | `dist/rules/ai_gemini.list` | 50 | 1.9 KB | 0 | 0 | 0 |
| 10 | 🤖 Claude & AI | `dist/rules/ai_other.list` | 147 | 4.2 KB | 251 | 78 | 4 |
| 11 | 🤖 微软助手 | `dist/rules/ai_copilot.list` | 31 | 1.1 KB | 9 | 5 | 0 |
| 12 | 📱 GV号服务 | `dist/rules/google_voice.list` | 4 | 0.3 KB | 0 | 0 | 0 |
| 13 | 📹 油管视频 | `dist/rules/youtube.list` | 177 | 4.9 KB | 1 | 0 | 0 |
| 14 | 🎥 奈飞视频 | `dist/rules/netflix.list` | 1262 | 43.3 KB | 1159 | 0 | 0 |
| 15 | 🎬 国际流媒体 | `dist/rules/intl_media.list` | 378 | 11.4 KB | 4 | 1 | 1 |
| 16 | 🎵 海外抖音 | `dist/rules/tiktok.list` | 39 | 1.4 KB | 1 | 0 | 0 |
| 17 | 🐉 巴哈姆特 | `dist/rules/bahamut.list` | 5 | 0.3 KB | 0 | 0 | 0 |
| 18 | 🎦 中站国际 | `dist/rules/bili_intl.list` | 5 | 0.3 KB | 3 | 0 | 0 |
| 19 | 📳 电报代理 | `dist/rules/telegram.list` | 33 | 1.1 KB | 24 | 0 | 0 |
| 20 | 🕊️ 推特代理 | `dist/rules/twitter.list` | 24 | 0.8 KB | 0 | 0 | 0 |
| 21 | 🪙 加密货币 | `dist/rules/crypto.list` | 241 | 6.6 KB | 0 | 0 | 0 |
| 22 | 🍎 苹果直连 | `dist/rules/apple_cn.list` | 150 | 4.9 KB | 2 | 11 | 4 |
| 23 | Ⓜ️ 微软直连 | `dist/rules/microsoft_cn.list` | 185 | 6.2 KB | 0 | 2 | 6 |
| 24 | 💻 开发与学术 | `dist/rules/dev_scholar.list` | 1438 | 41.6 KB | 92 | 28 | 0 |
| 25 | 🔎 谷歌服务 | `dist/rules/google.list` | 657 | 17.8 KB | 102 | 320 | 0 |
| 26 | 🍎 苹果服务 | `dist/rules/apple.list` | 1389 | 43.4 KB | 83 | 195 | 1 |
| 27 | Ⓜ️ 微软服务 | `dist/rules/microsoft.list` | 382 | 11.4 KB | 27 | 351 | 0 |
| 28 | 📺 国内媒体 | `dist/rules/cn_media.list` | 1547 | 42.4 KB | 217 | 55 | 0 |
| 29 | 🇨🇳 国内常用 | `dist/rules/cn_common.list` | 1148 | 31.4 KB | 257 | 11 | 0 |
| 30 | 🎮 国内游戏 | `dist/rules/cn_games.list` | 36 | 1.3 KB | 19 | 1 | 0 |
| 31 | 📶 网络测速 | `dist/rules/speedtest.list` | 19 | 0.7 KB | 0 | 0 | 1 |
| 32 | 📥 下载服务 | `dist/rules/download_pt.list` | 476 | 12.2 KB | 64 | 0 | 10 |
| 33 | 🧱 防火长城 | `dist/rules/gfw.list` | 4456 | 121.2 KB | 9031 | 542 | 28 |
| 34 | 📞 国内服务 | `dist/rules/cn_domain_1.list, cn_domain_2.list, cn_domain_3.list, cn_domain_4.list, cn_domain_5.list, cn_domain_6.list, cn_domain_7.list` | 107450 | 2793.3 KB | 6 | 2008 | 49 |

## 跨组父域遮蔽自动清理样本（前 25 条）

- `DOMAIN,o1158394.ingest.us.sentry.io` (🤖 Claude & AI) 已被更高优先级父域 `sentry.io` (🤖 OpenAI) 覆盖，已自动剔除死规则
- `DOMAIN,openaicom.imgix.net` (🤖 Claude & AI) 已被更高优先级父域 `openaicom.imgix.net` (🤖 OpenAI) 覆盖，已自动剔除死规则
- `DOMAIN,o33249.ingest.sentry.io` (🤖 Claude & AI) 已被更高优先级父域 `sentry.io` (🤖 OpenAI) 覆盖，已自动剔除死规则
- `DOMAIN,o33249.ingest.us.sentry.io` (🤖 Claude & AI) 已被更高优先级父域 `sentry.io` (🤖 OpenAI) 覆盖，已自动剔除死规则
- `DOMAIN,disney.my.sentry.io` (🎬 国际流媒体) 已被更高优先级父域 `sentry.io` (🤖 OpenAI) 覆盖，已自动剔除死规则
- `DOMAIN,appldnld.apple.com` (🍎 苹果直连) 已被更高优先级父域 `appldnld.apple.com` (⬆️ 苹果升级) 覆盖，已自动剔除死规则
- `DOMAIN,appldnld.g.aaplimg.com` (🍎 苹果直连) 已被更高优先级父域 `appldnld.g.aaplimg.com` (⬆️ 苹果升级) 覆盖，已自动剔除死规则
- `DOMAIN,mesu-cdn.apple.com.akadns.net` (🍎 苹果直连) 已被更高优先级父域 `mesu-cdn.apple.com.akadns.net` (⬆️ 苹果升级) 覆盖，已自动剔除死规则
- `DOMAIN,mesu.apple.com` (🍎 苹果直连) 已被更高优先级父域 `mesu.apple.com` (⬆️ 苹果升级) 覆盖，已自动剔除死规则
- `DOMAIN-SUFFIX,cn.bing.com` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.com` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN-SUFFIX,cn.bing.net` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.net` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN-SUFFIX,cn.mm.bing.net` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.net` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN-SUFFIX,r.bing.com` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.com` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN-SUFFIX,th.bing.com` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.com` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN,bj1.api.bing.com` (Ⓜ️ 微软直连) 已被更高优先级父域 `bing.com` (🤖 微软助手) 覆盖，已自动剔除死规则
- `DOMAIN,mesu-cdn.apple.com.akadns.net` (🍎 苹果服务) 已被更高优先级父域 `mesu-cdn.apple.com.akadns.net` (⬆️ 苹果升级) 覆盖，已自动剔除死规则
- `DOMAIN,www.speedtest.net.cdn.cloudflare.net` (📶 网络测速) 已被更高优先级父域 `cloudflare.net` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,academic-p2p.appspot.com` (📥 下载服务) 已被更高优先级父域 `appspot.com` (🔎 谷歌服务) 覆盖，已自动剔除死规则
- `DOMAIN,bttracker.debian.org` (📥 下载服务) 已被更高优先级父域 `debian.org` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,carbon-bonsai-621.appspot.com` (📥 下载服务) 已被更高优先级父域 `appspot.com` (🔎 谷歌服务) 覆盖，已自动剔除死规则
- `DOMAIN,mail.artixlinux.org` (📥 下载服务) 已被更高优先级父域 `artixlinux.org` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,torrent.fedoraproject.org` (📥 下载服务) 已被更高优先级父域 `fedoraproject.org` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,torrent.ubuntu.com` (📥 下载服务) 已被更高优先级父域 `ubuntu.com` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,torrents.artixlinux.org` (📥 下载服务) 已被更高优先级父域 `artixlinux.org` (💻 开发与学术) 覆盖，已自动剔除死规则
- `DOMAIN,torrents.linuxmint.com` (📥 下载服务) 已被更高优先级父域 `linuxmint.com` (💻 开发与学术) 覆盖，已自动剔除死规则
