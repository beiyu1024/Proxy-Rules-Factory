#!/usr/bin/env python3
"""
Proxy-Rules-Factory 核心自动化构建与治理引擎
职责：
1. 每日并发拉取社区最活跃规则源（MetaCubeX/meta-rules-dat 等）+ 个人定制覆盖。
2. 自动兼容解析 domain-set (+./裸域)、IP-CIDR/IP-CIDR6、标准 Clash classical 格式。
3. 剔除旁路由无效的 PROCESS-NAME，自动为所有 IP-CIDR/IP-CIDR6 补齐 no-resolve。
4. 按严格业务优先级执行【全局跨组去重 + 精确冲突消除 + 同组父域覆盖子域精简 + 跨组父域遮蔽检测】。
5. 自动输出：
   - dist/rules/*.list        （干净、零冲突、单文件严控 < 500KB 绝不被 subconverter 截断）
   - dist/Beiyu_Pro.ini       （完美兼容 subconverter 的终极模板，300s 合理测速、全正则防假节点、防空组退化）
   - dist/mihomo_mrs.yaml     （Mihomo 原生 .mrs 二进制 rule-providers 现代覆写模板，客户端 24h 热更新）
   - dist/AUDIT.md            （透明自动化审计报告）
"""

from __future__ import annotations

import concurrent.futures
import datetime
import ipaddress
import os
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DIST_DIR = ROOT / "dist"
RULES_OUT_DIR = DIST_DIR / "rules"

SUPPORTED_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "IP-CIDR",
    "IP-CIDR6",
    "IP-ASN",
    "DST-PORT",
}

MAX_SINGLE_LIST_BYTES = 500 * 1024  # 严控单文件 < 500KB，绝不触发 subconverter 截断


def fetch_url(url: str) -> Tuple[str, List[str], str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Proxy-Rules-Factory/2.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8", errors="ignore")
            return url, text.splitlines(), ""
    except Exception as e:
        return url, [], str(e)


def parse_line(raw: str) -> Tuple[str, str, List[str]] | None:
    """将 domain-set / ip-cidr / classical 规则统一规范为 (rtype, value, extras)。"""
    line = raw.strip()
    if not line or line.startswith("#") or line.startswith(";") or line.startswith("//"):
        return None
    if line in ("payload:", "rules:", "rule-providers:"):
        return None
    # 去掉行内注释
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    if line.startswith("- "):
        line = line[2:].strip().strip('"').strip("'")
    else:
        line = line.strip('"').strip("'")

    # 1. Classical 格式（含逗号）
    if "," in line:
        parts = [p.strip() for p in line.split(",")]
        rtype = parts[0].upper()
        if rtype == "PROCESS-NAME":
            return None  # 旁路由三层转发看不到客户端进程名，统一剔除
        if rtype not in SUPPORTED_TYPES or len(parts) < 2:
            return None
        val = parts[1].strip()
        if not val:
            return None
        extras = []
        if rtype in ("IP-CIDR", "IP-CIDR6"):
            # 验证合法 CIDR 并强制补齐 no-resolve
            try:
                net = ipaddress.ip_network(val, strict=False)
                val = str(net)
                rtype = "IP-CIDR6" if net.version == 6 else "IP-CIDR"
            except ValueError:
                return None
            extras = ["no-resolve"]
        elif rtype in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"):
            val = val.lower().lstrip(".")
            if not val or " " in val:
                return None
        return rtype, val, extras

    # 2. 纯 IP / CIDR（如 MetaCubeX geoip/*.list）
    try:
        net = ipaddress.ip_network(line, strict=False)
        rtype = "IP-CIDR6" if net.version == 6 else "IP-CIDR"
        return rtype, str(net), ["no-resolve"]
    except ValueError:
        pass

    # 3. Domain-set 格式（MetaCubeX geosite/*.list）
    if line.startswith("+."):
        dom = line[2:].strip().lower().lstrip(".")
        if dom and " " not in dom and "*" not in dom:
            return "DOMAIN-SUFFIX", dom, []
        return None
    if line.startswith("."):
        dom = line[1:].strip().lower().lstrip(".")
        if dom and " " not in dom and "*" not in dom:
            return "DOMAIN-SUFFIX", dom, []
        return None
    if line.startswith("full:"):
        dom = line[5:].strip().lower()
        if dom and " " not in dom:
            return "DOMAIN", dom, []
        return None
    if line.startswith("domain:"):
        dom = line[7:].strip().lower()
        if dom and " " not in dom:
            return "DOMAIN-SUFFIX", dom, []
        return None
    if line.startswith("regexp:") or line.startswith("keyword:") or "*" in line:
        return None

    # 裸域名 -> DOMAIN
    dom = line.lower()
    if re.match(r"^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$", dom) and "." in dom:
        return "DOMAIN", dom, []
    return None


def format_rule(rtype: str, val: str, extras: List[str]) -> str:
    if extras:
        return f"{rtype},{val},{','.join(extras)}"
    return f"{rtype},{val}"


def parent_suffixes(domain: str, include_self: bool) -> List[str]:
    parts = domain.split(".")
    start = 0 if include_self else 1
    res = []
    for i in range(start, len(parts) - 1):
        res.append(".".join(parts[i:]))
    return res


def build_ini_template(cfg: dict, group_files: List[Tuple[dict, int]]) -> str:
    owner = cfg["repo_owner"]
    repo = cfg["repo_name"]
    branch = cfg["repo_branch"]
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/dist/rules"

    # 排除公告/流量/返利/群组等机场信息假节点的精准负向前瞻正则
    valid_node_regex = (
        "^(?!.*(官网|订阅|刷新|剩余|流量|到期|过期|重置|邀请|返利|群组|tg群|TG群|通知|维护|客服|套餐|网址|发布页|失联)).*"
    )

    lines = [
        "[custom]",
        "; =====================================================================",
        f"; Proxy-Rules-Factory 自动生成分流模板 (Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})",
        "; 特点：零冲突 / 零父域杀子域 / 零体积截断 / 300s 合理测速 / 全正则防假节点 / 防空组退化",
        "; =====================================================================",
        "",
        "; ------------------ 分流规则集（严格按优先级从细到粗排列） ------------------",
    ]

    for grp, count in group_files:
        if count == 0:
            continue
        lines.append(f"ruleset={grp['name']},{raw_base}/{grp['id']}.list")

    # 国内外终极兜底（GEOIP,CN 放最后 MATCH 前，不加 no-resolve；OpenClash 旁路由同时叠加 GEOSITE,cn 加速）
    lines.extend([
        "ruleset=📞 国内IP段,[]GEOIP,CN",
        "ruleset=🐟 漏网之鱼,[]FINAL",
        "",
        "; ------------------ 业务策略组（安全默认项，杜绝空地区组退化直连） ------------------",
    ])

    # 公共节点候选池（精简清晰，去掉冗余空组）
    node_pool = (
        "[]♻️ 自动选择`[]🔯 故障转移`[]🔒 私人节点"
        "`[]🇭🇰 香港节点`[]🇹🇼 台湾节点`[]🇯🇵 日本节点`[]🇸🇬 狮城节点`[]🇺🇲 美国节点`[]🇰🇷 韩国节点`[]🌐 其他地区"
        "`[]✨ 指定节点1`[]✨ 指定节点2`[]🎯 直连服务`[]❌ 拒绝请求"
    )
    proxy_choices = f"[]☑️ 节点选择`{node_pool}"
    direct_choices = f"[]🎯 直连服务`[]☑️ 节点选择`{node_pool.replace('`[]🎯 直连服务', '')}"

    # 主力总选组
    lines.append(
        "custom_proxy_group=☑️ 节点选择`select`[]🔯 故障转移`[]♻️ 自动选择`[]🔒 私人节点"
        "`[]🇭🇰 香港节点`[]🇹🇼 台湾节点`[]🇯🇵 日本节点`[]🇸🇬 狮城节点`[]🇺🇲 美国节点`[]🇰🇷 韩国节点`[]🌐 其他地区"
        "`[]✨ 指定节点1`[]✨ 指定节点2`[]🎯 直连服务"
    )

    emitted_groups = {"☑️ 节点选择", "🏠 局域服务", "🎯 直连服务", "❌ 拒绝请求"}
    for grp, count in group_files:
        gname = grp["name"]
        if gname in emitted_groups or count == 0:
            continue
        emitted_groups.add(gname)
        dt = grp.get("default_target", "☑️ 节点选择")
        if dt == "🎯 直连服务":
            lines.append(f"custom_proxy_group={gname}`select`{direct_choices}")
        elif dt == "❌ 拒绝请求":
            lines.append(
                f"custom_proxy_group={gname}`select`[]❌ 拒绝请求`[]🎯 直连服务`[]☑️ 节点选择"
            )
        elif dt == "🔯 故障转移":
            lines.append(
                f"custom_proxy_group={gname}`select`[]🔯 故障转移`[]☑️ 节点选择`[]♻️ 自动选择`[]🔒 私人节点"
                "`[]🇭🇰 香港节点`[]🇸🇬 狮城节点`[]🇯🇵 日本节点`[]🇺🇲 美国节点`[]✨ 指定节点1"
            )
        elif dt == "🇺🇲 美国节点":
            # 若无美国节点，仍可快速切到 ☑️ 节点选择 / 私人节点
            lines.append(
                f"custom_proxy_group={gname}`select`[]🇺🇲 美国节点`[]☑️ 节点选择`[]🔒 私人节点`[]🔯 故障转移"
                "`[]♻️ 自动选择`[]✨ 指定节点1`[]🎯 直连服务"
            )
        else:
            lines.append(f"custom_proxy_group={gname}`select`{proxy_choices}")

    lines.extend([
        f"custom_proxy_group=📞 国内IP段`select`{direct_choices}",
        f"custom_proxy_group=🐟 漏网之鱼`select`{proxy_choices}",
        f"custom_proxy_group=✨ 指定节点1`select`{valid_node_regex}",
        f"custom_proxy_group=✨ 指定节点2`select`{valid_node_regex}",
        "",
        "; ------------------ 节点自动测速与地区分组（300s 合理间隔 / 50ms 容差，排除信息假节点） ------------------",
        f"custom_proxy_group=♻️ 自动选择`url-test`{valid_node_regex}`http://www.gstatic.com/generate_204`300,,50",
        f"custom_proxy_group=🔯 故障转移`fallback`{valid_node_regex}`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🔒 私人节点`url-test`(Beiyu|beiyu|82345679)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇭🇰 香港节点`url-test`(港|HK|hk|Hong Kong|HongKong)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇹🇼 台湾节点`url-test`(台|新北|彰化|TW|tw|Taiwan|湾)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇯🇵 日本节点`url-test`(日本|川日|东京|大阪|泉日|埼玉|沪日|深日|JP|jp|Japan)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇸🇬 狮城节点`url-test`(新加坡|坡|狮城|SG|sg|Singapore)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇺🇲 美国节点`url-test`(美|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|硅谷|拉斯维加斯|洛杉矶|圣何塞|圣克拉拉|西雅图|芝加哥|US|us|United States)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🇰🇷 韩国节点`url-test`(KR|kr|Korea|KOR|首尔|韩|韓)`http://www.gstatic.com/generate_204`300,,50",
        "custom_proxy_group=🌐 其他地区`url-test`^(?!.*(官网|订阅|刷新|剩余|流量|到期|过期|重置|邀请|返利|群组|tg群|TG群|通知|维护|客服|套餐|网址|发布页|失联|港|HK|hk|Hong Kong|HongKong|台|新北|彰化|TW|tw|Taiwan|湾|日本|川日|东京|大阪|泉日|埼玉|沪日|深日|JP|jp|Japan|新加坡|坡|狮城|SG|sg|Singapore|美|波特兰|达拉斯|俄勒冈|凤凰城|费利蒙|硅谷|拉斯维加斯|洛杉矶|圣何塞|圣克拉拉|西雅图|芝加哥|US|us|United States|KR|kr|Korea|KOR|首尔|韩|韓)).*`http://www.gstatic.com/generate_204`300,,50",
        "",
        "; 基础动作组（严禁对 DIRECT 做 url-test！）",
        "custom_proxy_group=🏠 局域服务`select`[]DIRECT",
        "custom_proxy_group=🎯 直连服务`select`[]DIRECT",
        "custom_proxy_group=❌ 拒绝请求`select`[]REJECT",
        "",
        "enable_rule_generator=true",
        "overwrite_original_rules=true",
        "",
    ])
    return "\n".join(lines)


def build_mihomo_mrs_template(cfg: dict, group_files: List[Tuple[dict, int]]) -> str:
    """生成 Mihomo 原生 .mrs 二进制 rule-providers 现代模板（客户端每 24h 自动热更新社区最新规则）。"""
    owner = cfg["repo_owner"]
    repo = cfg["repo_name"]
    branch = cfg["repo_branch"]
    own_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/dist/rules"
    mrs_geo = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo"

    providers = {}
    rules = []

    # 先放个人/自定义私有规则（classical text）+ MetaCubeX .mrs 二进制规则
    for grp, count in group_files:
        if count == 0:
            continue
        gid = grp["id"]
        gname = grp["name"]
        mrs_gs = grp.get("mrs_geosite") or []
        mrs_gi = grp.get("mrs_geoip") or []
        mrs_extra = grp.get("mrs_extra_urls") or []

        # 私有/自定义规则（或无 .mrs 对应的组）使用本仓库清洗后的 .list
        if grp.get("custom_key") or (not mrs_gs and not mrs_gi and not mrs_extra):
            pname = f"own_{gid}"
            providers[pname] = {
                "type": "http",
                "behavior": "classical",
                "format": "text",
                "url": f"{own_base}/{gid}.list",
                "path": f"./rule_provider/{pname}.list",
                "interval": 86400,
            }
            rules.append(f"RULE-SET,{pname},{gname}")

        for extra in mrs_extra:
            pname = extra["name"]
            if pname not in providers:
                providers[pname] = {
                    "type": "http",
                    "behavior": extra.get("behavior", "domain"),
                    "format": "mrs",
                    "url": extra["url"],
                    "path": f"./rule_provider/{pname}.mrs",
                    "interval": 86400,
                }
            rules.append(f"RULE-SET,{pname},{gname}")

        for gs in mrs_gs:
            pname = f"mrs_gs_{gs.replace('!', 'not_').replace('@', '_at_')}"
            if pname not in providers:
                providers[pname] = {
                    "type": "http",
                    "behavior": "domain",
                    "format": "mrs",
                    "url": f"{mrs_geo}/geosite/{gs}.mrs",
                    "path": f"./rule_provider/{pname}.mrs",
                    "interval": 86400,
                }
            rules.append(f"RULE-SET,{pname},{gname}")

        for gi in mrs_gi:
            pname = f"mrs_gi_{gi}"
            if pname not in providers:
                providers[pname] = {
                    "type": "http",
                    "behavior": "ipcidr",
                    "format": "mrs",
                    "url": f"{mrs_geo}/geoip/{gi}.mrs",
                    "path": f"./rule_provider/{pname}.mrs",
                    "interval": 86400,
                }
            rules.append(f"RULE-SET,{pname},{gname},no-resolve")

    # 社区每日自动更新的国内域名 + 国内 IP 二进制规则集
    providers["mrs_gs_cn"] = {
        "type": "http",
        "behavior": "domain",
        "format": "mrs",
        "url": f"{mrs_geo}/geosite/cn.mrs",
        "path": "./rule_provider/mrs_gs_cn.mrs",
        "interval": 86400,
    }
    providers["mrs_gi_cn"] = {
        "type": "http",
        "behavior": "ipcidr",
        "format": "mrs",
        "url": f"{mrs_geo}/geoip/cn.mrs",
        "path": "./rule_provider/mrs_gi_cn.mrs",
        "interval": 86400,
    }
    rules.append("RULE-SET,mrs_gs_cn,🎯 直连服务")
    rules.append("RULE-SET,mrs_gi_cn,📞 国内IP段")  # 不带 no-resolve，确保冷门国内域名也可解析判定直连
    rules.append("MATCH,🐟 漏网之鱼")

    doc = {
        "rule-providers": providers,
        "rules": rules,
    }
    header = (
        f"# Mihomo 原生 .mrs 二进制规则集模板 (Generated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})\n"
        "# 规则每 24 小时由 Mihomo 内核自动从 MetaCubeX/meta-rules-dat 与本仓库热更新，无需重新转换订阅。\n"
        "# 可直接用于 Clash Verge Rev / Mihomo Party / OpenClash 覆写脚本。\n\n"
    )
    return header + yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)


def main() -> int:
    sources_cfg = yaml.safe_load((CONFIG_DIR / "sources.yaml").read_text(encoding="utf-8"))
    custom_cfg = yaml.safe_load((CONFIG_DIR / "custom_overrides.yaml").read_text(encoding="utf-8"))

    custom_map: Dict[str, List[str]] = custom_cfg.get("custom_rules") or {}
    global_drops: Set[Tuple[str, str]] = set()
    for r in custom_cfg.get("global_drop_rules") or []:
        parsed = parse_line(r)
        if parsed:
            global_drops.add((parsed[0], parsed[1]))

    # 1. 收集并并发拉取所有上游 URL
    all_urls: Set[str] = set()
    for g in sources_cfg["groups"]:
        for u in g.get("sources") or []:
            all_urls.add(u)

    url_cache: Dict[str, List[str]] = {}
    fetch_errors: List[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for url, lines, err in ex.map(fetch_url, sorted(all_urls)):
            if err:
                fetch_errors.append(f"{url} -> {err}")
            else:
                url_cache[url] = lines

    if fetch_errors:
        print("ERROR: Failed to fetch some upstream sources:", file=sys.stderr)
        for e in fetch_errors:
            print("  -", e, file=sys.stderr)
        return 1

    # 2. 按严格优先级遍历分组：全局精确去重 + 同组父域覆盖子域精简 + 跨组父域防遮蔽记录
    RULES_OUT_DIR.mkdir(parents=True, exist_ok=True)
    # 清理旧 .list
    for old in RULES_OUT_DIR.glob("*.list"):
        old.unlink()

    global_seen: Dict[Tuple[str, str], str] = {}        # (rtype, val) -> winner group name
    global_suffix_owner: Dict[str, str] = {}            # suffix -> winner group name

    stats = []
    group_files: List[Tuple[dict, int]] = []
    total_raw = 0
    total_final = 0
    total_dup_dropped = 0
    total_conflict_dropped = 0
    total_shadow_dropped = 0
    shadow_samples: List[str] = []

    for grp in sources_cfg["groups"]:
        gid = grp["id"]
        gname = grp["name"]
        raw_lines: List[str] = []

        ckey = grp.get("custom_key")
        if ckey and ckey in custom_map:
            raw_lines.extend(custom_map[ckey])
        for u in grp.get("sources") or []:
            raw_lines.extend(url_cache.get(u, []))

        # 先收集本组所有合法规则
        parsed_items: List[Tuple[str, str, List[str]]] = []
        local_seen: Set[Tuple[str, str]] = set()
        raw_valid = 0
        dup_in_grp = 0
        conflict_drop = 0
        shadow_drop = 0

        for line in raw_lines:
            p = parse_line(line)
            if not p:
                continue
            rt, rv, ex = p
            if (rt, rv) in global_drops:
                continue
            raw_valid += 1
            if (rt, rv) in local_seen:
                dup_in_grp += 1
                continue
            local_seen.add((rt, rv))
            parsed_items.append((rt, rv, ex))

        # 本组内：先收集本组所有 DOMAIN-SUFFIX，用来清理本组内被父域覆盖的冗余子域
        local_suffixes = {rv for rt, rv, _ in parsed_items if rt == "DOMAIN-SUFFIX"}

        final_rules: List[str] = []
        for rt, rv, ex in parsed_items:
            # 1) 跨组精确冲突：已被更高优先级组占用，直接剔除（不产生死规则）
            if (rt, rv) in global_seen:
                conflict_drop += 1
                continue

            # 2) 本组内父域覆盖子域：冗余精简
            if rt in ("DOMAIN", "DOMAIN-SUFFIX"):
                parents = parent_suffixes(rv, include_self=(rt == "DOMAIN"))
                if any(p in local_suffixes for p in parents):
                    dup_in_grp += 1
                    continue
                # 3) 跨组父域遮蔽：已被更高优先级组的父域覆盖 -> 剔除并记录告警以便审计！
                hit_parent = next((p for p in parents if p in global_suffix_owner), None)
                if hit_parent:
                    shadow_drop += 1
                    if len(shadow_samples) < 25:
                        shadow_samples.append(
                            f"`{rt},{rv}` ({gname}) 已被更高优先级父域 `{hit_parent}` ({global_suffix_owner[hit_parent]}) 覆盖，已自动剔除死规则"
                        )
                    continue

            global_seen[(rt, rv)] = gname
            if rt == "DOMAIN-SUFFIX":
                global_suffix_owner[rv] = gname
            final_rules.append(format_rule(rt, rv, ex))

        # 排序使 git diff 干净稳定（先 DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、IP-CIDR、IP-CIDR6）
        type_order = {"DOMAIN": 0, "DOMAIN-SUFFIX": 1, "DOMAIN-KEYWORD": 2, "IP-CIDR": 3, "IP-CIDR6": 4, "IP-ASN": 5, "DST-PORT": 6}
        final_rules.sort(key=lambda s: (type_order.get(s.split(",", 1)[0], 9), s))

        out_file = RULES_OUT_DIR / f"{gid}.list"
        header = [
            f"# Group: {gname} ({gid})",
            f"# Updated: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"# Rules: {len(final_rules)} (raw={raw_valid}, local_dup={dup_in_grp}, cross_conflict={conflict_drop}, parent_shadow={shadow_drop})",
            "",
        ]
        content = "\n".join(header + final_rules) + "\n"
        out_bytes = len(content.encode("utf-8"))
        if out_bytes > MAX_SINGLE_LIST_BYTES:
            print(
                f"ERROR: {out_file.name} size {out_bytes} bytes exceeds safe subconverter limit ({MAX_SINGLE_LIST_BYTES} bytes)!",
                file=sys.stderr,
            )
            return 1

        out_file.write_text(content, encoding="utf-8")
        group_files.append((grp, len(final_rules)))

        total_raw += raw_valid
        total_final += len(final_rules)
        total_dup_dropped += dup_in_grp
        total_conflict_dropped += conflict_drop
        total_shadow_dropped += shadow_drop
        stats.append((gname, gid, len(final_rules), out_bytes, dup_in_grp, conflict_drop, shadow_drop))

    # 3. 输出 dist/Beiyu_Pro.ini
    ini_text = build_ini_template(sources_cfg, group_files)
    (DIST_DIR / "Beiyu_Pro.ini").write_text(ini_text, encoding="utf-8")

    # 4. 输出 dist/mihomo_mrs.yaml
    mrs_text = build_mihomo_mrs_template(sources_cfg, group_files)
    (DIST_DIR / "mihomo_mrs.yaml").write_text(mrs_text, encoding="utf-8")

    # 5. 输出 dist/AUDIT.md
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    audit_lines = [
        "# Proxy-Rules-Factory 自动构建审计报告",
        "",
        f"- **构建时间**：`{now_str}`",
        f"- **上游原始规则总量**：`{total_raw}` 条",
        f"- **清洗后输出规则总量**：`{total_final}` 条（零重复、零冲突、零死规则、零超限截断）",
        f"- **自动清理统计**：组内冗余 `{total_dup_dropped}` 条 ｜ 跨组精确冲突 `{total_conflict_dropped}` 条 ｜ 跨组父域遮蔽 `{total_shadow_dropped}` 条",
        "",
        "## 各业务分组产出明细（按优先级从高到低）",
        "",
        "| 优先级 | 策略组 | 文件 | 输出规则数 | 体积 | 组内去重 | 跨组冲突清理 | 父域遮蔽清理 |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
    ]
    for idx, (gname, gid, cnt, bsz, d1, d2, d3) in enumerate(stats, 1):
        kb = f"{bsz/1024:.1f} KB"
        audit_lines.append(f"| {idx} | {gname} | `dist/rules/{gid}.list` | {cnt} | {kb} | {d1} | {d2} | {d3} |")

    if shadow_samples:
        audit_lines.extend([
            "",
            "## 跨组父域遮蔽自动清理样本（前 25 条）",
            "",
        ])
        for s in shadow_samples:
            audit_lines.append(f"- {s}")

    (DIST_DIR / "AUDIT.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
    print(f"BUILD SUCCESS: {total_final} clean rules across {len(stats)} groups (raw={total_raw}, dropped={total_dup_dropped+total_conflict_dropped+total_shadow_dropped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
