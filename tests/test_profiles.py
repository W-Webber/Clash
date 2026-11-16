"""Offline checks for subscription templates and the companion OpenClash DNS backup."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOMESTIC = '➡️ 国内'
FINAL = '🐟 漏网之鱼'
DNS_PROXY = '港台日新韩-自动'
MIHOMO = {'Clash_wrt.ini', 'Clash_wrt_cdn.ini', 'Clash_fn.ini'}
PORTABLE = {'Clash.ini', 'Template.ini', 'Clash_qx.ini'}
BUILTINS = {'DIRECT', 'REJECT', 'REJECT-DROP', 'PASS', 'COMPATIBLE'}


def profile(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    rules = [line.split('=', 1)[1] for line in lines if line.startswith('ruleset=')]
    groups = {}
    for line in lines:
        if line.startswith('custom_proxy_group='):
            name, kind, *items = line.split('=', 1)[1].split('`')
            if name in groups:
                raise ValueError(f'Duplicate group: {name}')
            groups[name] = (kind, items)
    return lines, rules, groups


def uci_sections():
    text = (ROOT / 'openclash').read_text(encoding='utf-8')
    result = []
    for block in re.split(r'(?m)(?=^config )', text):
        if not block.startswith('config '):
            continue
        head = block.splitlines()[0]
        pairs = re.findall(r"(?m)^\s*option\s+(\w+)\s+'([^']*)'\s*$", block)
        if len({key for key, _ in pairs}) != len(pairs):
            raise ValueError(f'Duplicate UCI option in {head}')
        result.append((head, dict(pairs)))
    return result


class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.paths = sorted(ROOT.glob('*.ini'))

    def test_all_six_profiles_are_covered(self):
        self.assertEqual({p.name for p in self.paths}, MIHOMO | PORTABLE)

    def test_rule_order_and_independent_final(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, rules, _ = profile(path)
                self.assertTrue(rules[0].startswith('⛔ 广告,'))
                self.assertTrue(rules[1].startswith('🚫 屏蔽,'))
                self.assertTrue(rules[2].startswith(DOMESTIC + ','))
                self.assertEqual(rules[-1], FINAL + ',[]FINAL')
                self.assertEqual(sum(',[]FINAL' in x or ',[]MATCH' in x for x in rules), 1)
                self.assertEqual(sum(x.startswith(DOMESTIC + ',') for x in rules), 2)
                geoip_rules = [x for x in rules if ',[]GEOIP,' in x]
                self.assertEqual(geoip_rules, [DOMESTIC + ',[]GEOIP,CN,no-resolve'])
                self.assertEqual(rules[-2], geoip_rules[0])

    def test_client_specific_domestic_rules(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, rules, _ = profile(path)
                if path.name in MIHOMO:
                    self.assertEqual(rules[2], DOMESTIC + ',[]GEOSITE,cn')
                else:
                    self.assertIn(',clash-domain:https://', rules[2])
                    self.assertIn('/China/China_Domain.yaml,86400', rules[2])
                    self.assertFalse(any('GEOSITE' in x for x in rules))

    def test_defaults_domestic_direct_final_proxy(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, _, groups = profile(path)
                self.assertEqual(groups[DOMESTIC][0], 'select')
                self.assertEqual(groups[DOMESTIC][1][0], '[]DIRECT')
                self.assertEqual(groups[FINAL][0], 'select')
                self.assertEqual(groups[FINAL][1][0], '[]' + DNS_PROXY)
                for choice in ['[]DIRECT', '[]所有-手动', '[]REJECT']:
                    self.assertTrue(any(x.split(',img-url=', 1)[0] == choice for x in groups[FINAL][1]))

    def test_all_rule_and_group_references_exist(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, rules, groups = profile(path)
                allowed = groups.keys() | BUILTINS
                for rule in rules:
                    self.assertIn(rule.split(',', 1)[0], allowed)
                for name, (_, items) in groups.items():
                    for item in items:
                        if item.startswith('[]'):
                            target = item[2:].split(',img-url=', 1)[0]
                            self.assertIn(target, allowed, f'{name} -> {target}')
                            self.assertNotEqual(name, target)

    def test_group_graph_has_no_cycles(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, _, groups = profile(path)
                done = set()
                def visit(name, pending):
                    self.assertNotIn(name, pending, f'Group cycle: {pending} -> {name}')
                    if name in done:
                        return
                    for item in groups[name][1]:
                        if item.startswith('[]'):
                            target = item[2:].split(',img-url=', 1)[0]
                            if target in groups:
                                visit(target, pending | {name})
                    done.add(name)
                for name in groups:
                    visit(name, set())

    def test_dns_proxy_is_only_real_nodes(self):
        for path in self.paths:
            with self.subTest(profile=path.name):
                _, _, groups = profile(path)
                kind, items = groups[DNS_PROXY]
                self.assertEqual(kind, 'url-test')
                self.assertFalse(any(x.startswith('[]') for x in items))
                self.assertNotIn('DIRECT', items[0])

    def test_quantumult_icons_and_platform_settings_preserved(self):
        lines, _, groups = profile(ROOT / 'Clash_qx.ini')
        self.assertIn('quanx_rule_base=base/templates/quanx_custom.conf', lines)
        self.assertIn(',img-url=', groups[FINAL][1][-1])
        self.assertIn('clash.external_ui=/etc/mihomo/ui', profile(ROOT / 'Clash_fn.ini')[0])
        self.assertNotIn('clash.external_ui=/etc/mihomo/ui', profile(ROOT / 'Clash_wrt.ini')[0])

    def test_cdn_profile_keeps_its_remote_rule_urls(self):
        _, rules, _ = profile(ROOT / 'Clash_wrt_cdn.ini')
        for rule in rules:
            if 'https://' in rule:
                self.assertIn('https://cdn.jsdelivr.net/gh/', rule)

    def test_openclash_dns_flags(self):
        config = next(opts for head, opts in uci_sections() if head == "config openclash 'config'")
        self.assertEqual(config['append_wan_dns'], '0')
        self.assertEqual(config['append_default_dns'], '0')
        self.assertEqual(config['enable_custom_dns'], '1')
        self.assertEqual(config['enable_respect_rules'], '0')
        self.assertEqual(config['custom_name_policy'], '1')
        self.assertEqual(config['geosite_auto_update'], '1')

    def test_enabled_dns_records_do_not_mix_isp_into_nameserver(self):
        records = [opts for head, opts in uci_sections() if head == 'config dns_servers' and opts.get('enabled', '1') == '1']
        self.assertEqual(len(records), 3)
        ordinary = [opts for opts in records if opts['group'] == 'nameserver']
        self.assertEqual(len(ordinary), 1)
        self.assertEqual(ordinary[0]['ip'], '1.1.1.1/dns-query')
        self.assertEqual(ordinary[0]['type'], 'https')
        self.assertEqual(ordinary[0]['specific_group'], DNS_PROXY)
        self.assertEqual(ordinary[0]['node_resolve'], '0')
        self.assertEqual(ordinary[0]['direct_nameserver'], '0')
        bootstrap = [opts for opts in records if opts['group'] == 'default']
        self.assertEqual({opts['ip'] for opts in bootstrap}, {'202.102.224.68', '202.102.227.68'})
        for opts in bootstrap:
            self.assertEqual(opts['type'], 'udp')
            self.assertEqual(opts['node_resolve'], '1')
            self.assertEqual(opts['direct_nameserver'], '1')
            self.assertEqual(opts['specific_group'], 'Disable')

if __name__ == '__main__':
    unittest.main()