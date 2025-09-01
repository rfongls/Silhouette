from pathlib import Path
import datetime as dt
import click
import json
from .util.gates import require_ack_authorized, POLICY_BANNER_PATH
from .util.io import RunIO
from .evidence.collector import collect_evidence, build_evidence_pack
from .controls.mapper import map_controls
from .scan import dispatch_scan
from .report.writer import write_report

_policy_text = (
    POLICY_BANNER_PATH.read_text().strip()
    if POLICY_BANNER_PATH.exists()
    else "Authorized use only"
)
banner = f"Cybersecurity utilities. {_policy_text}"


@click.group(help=banner, context_settings={"help_option_names": ["-h","--help"]})
@click.option('--out', default='out/security', show_default=True, help='Output root directory')
@click.option('--scope', default='', help='Scope file or CIDR')
@click.option('--ack-authorized', is_flag=True, help='Acknowledge authorization requirements')
@click.pass_context
def cli(ctx, out, scope, ack_authorized):
    ctx.ensure_object(dict)
    ctx.obj['out'] = out
    ctx.obj['scope'] = scope
    ctx.obj['ack'] = ack_authorized
    ctx.obj['runio'] = RunIO(out)


def _record(ctx, cmd_name: str, args: dict):
    runio: RunIO = ctx.obj['runio']
    run_dir = runio.current_or_new_run_dir()
    meta = {'cmd': cmd_name, 'args': args, 'ts': dt.datetime.utcnow().isoformat()}
    runio.write_manifest(run_dir, meta)
    return run_dir


@cli.command('evidence')
@click.option('--source', type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True)
@click.pass_context
def evidence_cmd(ctx, source, dry_run):
    run_dir = _record(ctx, 'evidence', {'source': source, 'dry_run': dry_run})
    if dry_run:
        out_root = Path(ctx.obj['out'])
        out_root.mkdir(parents=True, exist_ok=True)
        (out_root / 'evidence_stub.txt').write_text('dry run')
        click.echo(str(run_dir))
        return
    if not source:
        raise click.ClickException('Missing option --source')
    collect_evidence(Path(source), run_dir)
    click.echo(str(run_dir))


@cli.command('map-controls')
@click.option('--framework', required=True)
@click.option('--evidence', required=True, type=click.Path(exists=True))
@click.option('--dry-run', is_flag=True)
@click.pass_context
def map_controls_cmd(ctx, framework, evidence, dry_run):
    run_dir = _record(ctx, 'map-controls', {'framework': framework, 'dry_run': dry_run})
    if not dry_run:
        map_controls(framework, Path(evidence), run_dir)
    click.echo(str(run_dir))


@cli.command('scan')
@click.option('--tool', required=True)
@click.option('--target', required=True)
@click.option('--use-seed', is_flag=True)
@click.option('--exec-real', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.pass_context
def scan_cmd(ctx, tool, target, use_seed, exec_real, dry_run):
    run_dir = _record(ctx, 'scan', {'tool': tool, 'target': target, 'use_seed': use_seed, 'exec_real': exec_real, 'dry_run': dry_run})
    if not dry_run:
        dispatch_scan(tool, target, run_dir, use_seed, exec_real, dry_run)
    click.echo(str(run_dir))


@cli.command('report')
@click.option('--format', 'fmt', type=click.Choice(['md', 'html', 'pdf']), default='html')
@click.option('--in', 'in_dir', required=True, type=click.Path(exists=True))
@click.option('--offline', is_flag=True)
@click.pass_context
def report_cmd(ctx, fmt, in_dir, offline):
    run_dir = Path(in_dir)
    write_report(run_dir, fmt)
    _record(ctx, 'report', {'format': fmt, 'in': in_dir, 'offline': offline})
    build_evidence_pack(run_dir)
    click.echo(str(run_dir / 'report'))


@cli.group('pentest')
@click.pass_context
def pentest_group(ctx):
    if not ctx.obj.get('ack'):
        require_ack_authorized(False)


@pentest_group.command('recon')
@click.option('--target', required=True, help='Target hostname/domain (must be in scope)')
@click.option('--scope-file', default='docs/cyber/scope_example.txt', show_default=True, help='Scope file path')
@click.option('--profile', default='safe', type=click.Choice(['safe','version','full']), show_default=True)
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_recon(ctx, target, scope_file, profile, dry_run):
    """Scaffold: call recon tool wrapper behind the pentest gate."""
    run_dir = _record(ctx, 'pentest.recon', {'target': target, 'scope_file': scope_file, 'profile': profile, 'dry_run': dry_run})
    if dry_run:
        click.echo(str(run_dir))
        return
    # use the scaffolded tool API
    try:
        from silhouette_core.skills.cyber_recon_scan.v1.wrapper import tool as recon_tool
        payload = json.dumps({
            "target": target,
            "scope_file": scope_file,
            "profile": profile,
            "out_dir": str(run_dir),
        })
        result = json.loads(recon_tool(payload))
        if not result.get("ok"):
            raise click.ClickException(f"Denied: {result.get('deny')}")
        click.echo(result.get("result"))
    except Exception as e:
        raise click.ClickException(str(e))


@pentest_group.command('gate')
@click.option('--target', required=True, help='Target hostname/domain (must be in scope)')
@click.option('--scope-file', default='docs/cyber/scope_example.txt', show_default=True, help='Scope file path')
@click.option('--auth-doc', required=True, help='Authorization document path')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_gate(ctx, target, scope_file, auth_doc, dry_run):
    """Scaffold: validate pentest authorization before running."""
    run_dir = _record(ctx, 'pentest.gate', {'target': target, 'scope_file': scope_file, 'auth_doc': auth_doc, 'dry_run': dry_run})
    if dry_run:
        click.echo(str(run_dir))
        return
    try:
        from silhouette_core.skills.cyber_pentest_gate.v1.wrapper import tool as gate_tool
        payload = json.dumps({
            'target': target,
            'scope_file': scope_file,
            'auth_doc': auth_doc,
            'out_dir': str(run_dir),
        })
        result = json.loads(gate_tool(payload))
        if not result.get('ok'):
            raise click.ClickException(f"Denied: {result.get('deny')}")
        click.echo(result.get('result'))
    except Exception as e:
        raise click.ClickException(str(e))


@pentest_group.command('playbook')
@click.option('--incident', default='generic', show_default=True, help='Incident type')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_playbook(ctx, incident, dry_run):
    """Scaffold: generate an incident response playbook stub."""
    run_dir = _record(ctx, 'pentest.playbook', {'incident': incident, 'dry_run': dry_run})
    if dry_run:
        click.echo(str(run_dir))
        return
    try:
        from silhouette_core.skills.cyber_ir_playbook.v1.wrapper import tool as pb_tool
        payload = json.dumps({'incident': incident, 'out_dir': str(run_dir)})
        result = json.loads(pb_tool(payload))
        if not result.get('ok'):
            raise click.ClickException(result.get('deny', 'error'))
        click.echo(result.get('result'))
    except Exception as e:
        raise click.ClickException(str(e))


@pentest_group.command('netforensics')
@click.option('--pcap', default='', help='PCAP file path')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_netforensics(ctx, pcap, dry_run):
    """Scaffold: process network captures."""
    run_dir = _record(ctx, 'pentest.netforensics', {'pcap': pcap, 'dry_run': dry_run})
    if dry_run:
        click.echo(str(run_dir))
        return
    try:
        from silhouette_core.skills.cyber_netforensics.v1.wrapper import tool as nf_tool
        payload = json.dumps({'pcap': pcap, 'out_dir': str(run_dir)})
        result = json.loads(nf_tool(payload))
        if not result.get('ok'):
            raise click.ClickException(result.get('deny', 'error'))
        click.echo(result.get('result'))
    except Exception as e:
        raise click.ClickException(str(e))


@pentest_group.command('net-survey')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_netsurvey(ctx, dry_run):
    run_dir = _record(ctx, 'pentest.net-survey', {'dry_run': dry_run})
    click.echo(str(run_dir))


@pentest_group.command('dast')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_dast(ctx, dry_run):
    run_dir = _record(ctx, 'pentest.dast', {'dry_run': dry_run})
    click.echo(str(run_dir))


@pentest_group.command('api')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pentest_api(ctx, dry_run):
    run_dir = _record(ctx, 'pentest.api', {'dry_run': dry_run})
    click.echo(str(run_dir))

# placeholders for other subcommands and stubs
@cli.command('assess')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def assess_cmd(ctx, dry_run):
    run_dir = _record(ctx, 'assess', {'dry_run': dry_run})
    click.echo(str(run_dir))

@cli.command('capture')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def capture_cmd(ctx, dry_run):
    run_dir = _record(ctx, 'capture', {'dry_run': dry_run})
    click.echo(str(run_dir))

@cli.command('pcap')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def pcap_cmd(ctx, dry_run):
    run_dir = _record(ctx, 'pcap', {'dry_run': dry_run})
    click.echo(str(run_dir))


@cli.command('ids')
@click.option('--engine', default='zeek')
@click.option('--dry-run', is_flag=True)
@click.pass_context
def ids_cmd(ctx, engine, dry_run):
    run_dir = _record(ctx, 'ids', {'engine': engine, 'dry_run': dry_run})
    click.echo(str(run_dir))


__all__ = ['cli']
