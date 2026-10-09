"""`minicloud` CLI: start/stop/status/destroy-all/logs/init-terraform."""

import json
import os
import signal
import subprocess
import sys
import time

import click

PID_FILE = os.path.join(os.getcwd(), ".minicloud.pid")
PORT = int(os.environ.get("MINICLOUD_PORT", 4566))

PROVIDER_TF = """\
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true

  endpoints {
    ec2 = "http://localhost:%d"
    s3  = "http://localhost:%d"
    iam = "http://localhost:%d"
    sqs = "http://localhost:%d"
    dynamodb = "http://localhost:%d"
  }
}
""" % (PORT, PORT, PORT, PORT, PORT)


@click.group()
def cli():
    """MiniCloud — a local AWS emulator backed by real Docker containers."""


@cli.command()
@click.option("--background/--foreground", default=False, help="Run the server in the background.")
@click.option("--port", default=PORT, help="Port to listen on.")
def start(background, port):
    """Start the MiniCloud API server."""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if _pid_alive(pid):
            click.echo(f"MiniCloud is already running (pid {pid}).")
            return

    if background:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        proc = subprocess.Popen(
            [sys.executable, "-m", "minicloud.server"],
            env={**os.environ, "MINICLOUD_PORT": str(port)},
            creationflags=creationflags,
            stdout=open("minicloud.log", "a"),
            stderr=subprocess.STDOUT,
        )
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        click.echo(f"MiniCloud started in background (pid {proc.pid}), logging to minicloud.log")
    else:
        from . import server
        server.run(port=port, foreground=True)


@cli.command()
def stop():
    """Stop a background MiniCloud server."""
    if not os.path.exists(PID_FILE):
        click.echo("MiniCloud is not running (no pid file).")
        return
    with open(PID_FILE) as f:
        pid = int(f.read().strip())
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        click.echo(f"Stopped MiniCloud (pid {pid}).")
    except Exception as e:
        click.echo(f"Could not stop pid {pid}: {e}")
    os.remove(PID_FILE)


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


@cli.command()
def status():
    """List all MiniCloud-managed resources and their Docker containers."""
    from . import state_db
    from . import docker_manager

    state_db.init_db()
    resources = state_db.list_resources()
    if not resources:
        click.echo("No MiniCloud-managed resources yet.")
    else:
        click.echo(f"{'TYPE':<14} {'RESOURCE ID':<24} {'DOCKER NAME':<32} {'STATE':<10}")
        for r in resources:
            state = r["extra"].split(";")[0].replace("state=", "") if r["extra"] else ""
            click.echo(f"{r['resource_type']:<14} {r['resource_id']:<24} {r['docker_name'] or '-':<32} {state:<10}")

    click.echo()
    click.echo(f"Docker available: {docker_manager.DOCKER_AVAILABLE}")
    if docker_manager.DOCKER_AVAILABLE:
        containers = docker_manager.list_managed_containers()
        click.echo(f"Managed containers: {len(containers)}")
        for c in containers:
            click.echo(f"  {c['name']}  [{c['status']}]  resource={c['resource_id']}")


@cli.command(name="destroy-all")
@click.option("--force", is_flag=True, help="Skip the confirmation prompt.")
def destroy_all(force):
    """Remove ALL MiniCloud-managed containers, networks, and state. Works
    even if Terraform state is lost."""
    from . import docker_manager
    from . import state_db

    if not force:
        click.confirm(
            "This will remove ALL MiniCloud-managed Docker containers and networks. Continue?",
            abort=True,
        )
    removed = docker_manager.destroy_all_managed_resources()
    state_db.init_db()
    state_db.clear_all()
    click.echo(f"Removed {removed['containers']} container(s), {removed['networks']} network(s).")


cli.add_command(destroy_all, name="reset")


@cli.command()
@click.argument("resource_id")
@click.option("--tail", default=200, help="Number of log lines to show.")
def logs(resource_id, tail):
    """Show a managed container's logs by resource id or Docker container id."""
    from . import state_db
    from . import docker_manager

    state_db.init_db()
    res = state_db.get_resource(resource_id)
    container_id = res["docker_id"] if res else resource_id
    click.echo(docker_manager.container_logs(container_id, tail=tail))


@cli.command(name="init-terraform")
@click.option("--dir", "target_dir", default=".", help="Directory to write provider.tf into.")
def init_terraform(target_dir):
    """Generate a ready-to-use provider.tf with MiniCloud's endpoint overrides."""
    path = os.path.join(target_dir, "provider.tf")
    with open(path, "w") as f:
        f.write(PROVIDER_TF)
    click.echo(f"Wrote {path}")
    click.echo("Next: terraform init && terraform plan && terraform apply")


def main():
    cli()


if __name__ == "__main__":
    main()
