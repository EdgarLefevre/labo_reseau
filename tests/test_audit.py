from netlab.audit import (
    check_addressing,
    check_any_any,
    check_default_policies,
    check_snmp,
)

GOOD = """table inet filter {
\tchain input {
\t\ttype filter hook input priority filter; policy drop;
\t}
\tchain forward {
\t\ttype filter hook forward priority filter; policy drop;
\t\tct state established,related accept
\t}
}"""

BAD = GOOD.replace("policy drop; \n\t}\n\tchain forward", "policy accept;\n\t}\n\tchain forward") + "\n\t\taccept"


def test_good_ruleset_is_compliant():
    assert check_default_policies(GOOD) == []
    assert check_any_any(GOOD) == []


def test_accept_policy_is_detected():
    findings = check_default_policies(GOOD.replace("input priority filter; policy drop",
                                                   "input priority filter; policy accept"))
    assert [f.rule for f in findings] == ["default-policy"]


def test_any_any_is_detected():
    assert len(check_any_any(GOOD + "\n\t\taccept")) == 1


def test_address_outside_plan_is_detected():
    data = '[{"ifname": "eth3", "addr_info": [{"family": "inet", "local": "172.31.0.5"}]}]'
    assert check_addressing(data)[0].rule == "addressing"


def test_default_snmp_community_is_detected():
    assert check_snmp("snmp-server community public")[0].severity == "HIGH"