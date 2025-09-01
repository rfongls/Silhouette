import json, sys
try:
    import click
except Exception:
    click = None

def _print_result(res: str) -> None:
    try:
        data = json.loads(res)
        print(data.get("result", res))
    except Exception:
        print(res)

def _security_argparse_main():
    import argparse
    from silhouette_core.skills.cyber_pentest_gate.v1.wrapper import tool as gate_tool
    from silhouette_core.skills.cyber_recon_scan.v1.wrapper import tool as recon_tool
    from silhouette_core.skills.cyber_netforensics.v1.wrapper import tool as netf_tool
    from silhouette_core.skills.cyber_ir_playbook.v1.wrapper import tool as play_tool
    p = argparse.ArgumentParser(prog="silhouette security (fallback)")
    sub = p.add_subparsers(dest="cmd", required=True)
    spg = sub.add_parser("gate")
    spg.add_argument("--target", required=True)
    spg.add_argument("--scope-file", required=True)
    spg.add_argument("--auth-doc", required=True)
    spg.add_argument("--out", dest="out_dir")
    spr = sub.add_parser("recon")
    spr.add_argument("--target", required=True)
    spr.add_argument("--scope-file", required=True)
    spr.add_argument("--profile", choices=["safe","version","full"], default="safe")
    spr.add_argument("--out", dest="out_dir")
    spn = sub.add_parser("netforensics")
    spn.add_argument("--pcap", required=True)
    spn.add_argument("--out", dest="out_dir")
    spp = sub.add_parser("playbook")
    spp.add_argument("--incident", default="ransomware")
    spp.add_argument("--out", dest="out_dir")
    args = p.parse_args()
    payload = json.dumps(vars(args))
    if args.cmd == "gate":
        _print_result(gate_tool(payload))
    elif args.cmd == "recon":
        _print_result(recon_tool(payload))
    elif args.cmd == "netforensics":
        _print_result(netf_tool(payload))
    elif args.cmd == "playbook":
        _print_result(play_tool(payload))

if click is None:
    if __name__ == "__main__":
        _security_argparse_main()
        raise SystemExit(0)
else:
    @click.group(context_settings={"help_option_names": ["-h","--help"]})
    def main():
        ...

    @main.group("security")
    @click.option("--ack-authorized", is_flag=True, default=False)
    @click.pass_context
    def security(ctx, ack_authorized):
        ctx.ensure_object(dict)
        ctx.obj["ack"] = ack_authorized

    @security.group("pentest")
    @click.pass_context
    def pentest(ctx):
        if not ctx.obj.get("ack"):
            raise click.ClickException("Denied: missing --ack-authorized")

    @pentest.command("gate")
    @click.option("--target", required=True)
    @click.option("--scope-file", required=True)
    @click.option("--auth-doc", required=True)
    @click.option("--out", "out_dir", default=None)
    def pentest_gate(target, scope_file, auth_doc, out_dir):
        from silhouette_core.skills.cyber_pentest_gate.v1.wrapper import tool
        res = tool(json.dumps({"target": target, "scope_file": scope_file, "auth_doc": auth_doc, "out_dir": out_dir}))
        _print_result(res)

    @pentest.command("recon")
    @click.option("--target", required=True)
    @click.option("--scope-file", required=True)
    @click.option("--profile", type=click.Choice(["safe", "version", "full"]), default="safe")
    @click.option("--out", "out_dir", default=None)
    def pentest_recon(target, scope_file, profile, out_dir):
        from silhouette_core.skills.cyber_recon_scan.v1.wrapper import tool
        res = tool(json.dumps({"target": target, "scope_file": scope_file, "profile": profile, "out_dir": out_dir}))
        _print_result(res)

    @pentest.command("netforensics")
    @click.option("--pcap", required=True)
    @click.option("--out", "out_dir", default=None)
    def pentest_netforensics(pcap, out_dir):
        from silhouette_core.skills.cyber_netforensics.v1.wrapper import tool
        res = tool(json.dumps({"pcap": pcap, "out_dir": out_dir}))
        _print_result(res)

    @pentest.command("playbook")
    @click.option("--incident", default="ransomware")
    @click.option("--out", "out_dir", default=None)
    def pentest_playbook(incident, out_dir):
        from silhouette_core.skills.cyber_ir_playbook.v1.wrapper import tool
        res = tool(json.dumps({"incident": incident, "out_dir": out_dir}))
        _print_result(res)

    if __name__ == "__main__":
        main()
