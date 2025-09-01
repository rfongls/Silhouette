from pathlib import Path
import click

POLICY_BANNER_PATH = Path('configs/security/policy_banner.txt')
ACTIVE_COMMANDS = {"pentest"}


def is_active_command(cmd: str) -> bool:
    return cmd in ACTIVE_COMMANDS


def require_ack_authorized(flag: bool) -> None:
    if not flag:
        banner = POLICY_BANNER_PATH.read_text().strip() if POLICY_BANNER_PATH.exists() else "Authorization required"
        raise click.ClickException(f"{banner}\nPass --ack-authorized to proceed with active commands.")
