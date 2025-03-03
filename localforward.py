import argparse
import os
import re
import subprocess
import sys
import json
from pathlib import Path
import signal
import paramiko # type: ignore
from typing import Any

TUNNEL_PID_FILE = "/tmp/localforward_tunnel.pid"
TUNNEL_LOG_FILE = "/tmp/localforward.log"
TUNNEL_PROFILE_FILE = "/tmp/localforward_profile"

CONFIG_FILE = Path.home() / '.localforward_config.json'
LOOPBACK_PREFIX = '127.0.0.'
START_IP = 2
END_IP = 255

# LocalForward tag to manage only relevant entries in /etc/hosts
LOCALFORWARD_TAG = '# Added by LocalForward'

if not CONFIG_FILE.exists():
    CONFIG_FILE.write_text(json.dumps({'default_profile': None}))

with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

def set_default_ssh_profile(profile: str):
    config['default_profile'] = profile
    CONFIG_FILE.write_text(json.dumps(config))

def execute_command(command: str):
    print(f'Executing: {command}')
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f'Error executing: {command}')
        sys.exit(1)


def get_available_ip(host_name: str):
    used_ips = set()
    with open('/etc/hosts', 'r') as f:
        for line in f.readlines():
            match = re.match(r'127\.0\.0\.(\d+)\s.+\s'+LOCALFORWARD_TAG+'$', line)
            if match:
                parts = line.split()
                existing_host = parts[1]
                if existing_host == host_name:
                    print(f"🚦 {host_name} is already configured")
                    sys.exit(0)
                used_ips.add(int(match.group(1)))
    
    for i in range(START_IP, END_IP):
        if i not in used_ips:
            return f'{LOOPBACK_PREFIX}{i}'
    print('No available loopback IPs')
    sys.exit(1)


def add_host(host_name: str):
    ip_address = get_available_ip(host_name)
    print(f'Assigning {ip_address} to {host_name}')
    with open('/etc/hosts', 'a') as f:
        f.write(f'{ip_address} {host_name} {LOCALFORWARD_TAG}\n')
    execute_command(f'sudo ifconfig lo0 alias {ip_address}')
    print(f'✅ Host {host_name} added with IP {ip_address}')
    restart_ssh_tunnel()

def restart_ssh_tunnel():
    with open(TUNNEL_PID_FILE, "r") as f:
        pid = int(f.read().strip())

    if pid:
        stop_tunnel()
        start_ssh_tunnel()

def get_ssh_profile_details(ssh_profile):
    try:
        if not ssh_profile:
            ssh_profile = config.get('default_profile')
        if not ssh_profile:
            print('❌ Error: SSH profile is required. Set a default with "localforward ssh-profile {profile}" or provide with "localforward start {profile}".')
            sys.exit(1)
        
        set_default_ssh_profile(ssh_profile)
        ssh_config_path = os.path.expanduser("~/.ssh/config")
        if not os.path.exists(ssh_config_path):
            raise FileNotFoundError(f"{ssh_config_path} not found.")
        
        with open(ssh_config_path, "r") as f:
            ssh_config = paramiko.SSHConfig()
            ssh_config.parse(f)

        profile = ssh_config.lookup(ssh_profile)
        if profile:
                return profile 
        return None
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting SSH config for {ssh_profile}: {e}", file=sys.stderr)
        return None


def start_tunnel(ssh_config: dict[str, Any | None]):
    hostname,user, identityfile = ssh_config.values()

    ssh_command = ['ssh', '-i', identityfile[0], '-v']

    with open('/etc/hosts', 'r') as f:
        for line in f.readlines():
            match = re.match(r'(127\.0\.0\.\d+)\s(.+)\s'+LOCALFORWARD_TAG+'$', line)
            if match:
                ip_address, host_name = match.groups()
                ssh_command.extend(['-L', f'{ip_address}:80:{host_name}:80'])

    ssh_command.append(f'{user}@{hostname}')

    with open(TUNNEL_LOG_FILE, "w") as log_file:
        process = subprocess.Popen(ssh_command, stdout=log_file, stderr=subprocess.STDOUT)
     
    with open(TUNNEL_PID_FILE, "w") as pid_file:
        pid_file.write(str(process.pid))

    print(f"🔗 SSH tunnel started with PID {process.pid}, Logs available at {TUNNEL_LOG_FILE}")

def show_logs():
    try:
        subprocess.run(["tail", "-f", TUNNEL_LOG_FILE])
    except KeyboardInterrupt:
        print("Stopping log view")


def set_default_profile(profile: str):
    config['default_profile'] = profile
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    print(f'✅ Default SSH profile set to {profile}')


def stop_tunnel():
    if not os.path.exists(TUNNEL_PID_FILE):
        print("❌ No active SSH tunnel found.")
        return

    with open(TUNNEL_PID_FILE, "r") as f:
        pid = int(f.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Stopped SSH tunnel with PID {pid}")
    except ProcessLookupError as e:
        print("❌ SSH tunnel is not running.")

    os.remove(TUNNEL_PID_FILE)


def ensure_sudo():
    if os.geteuid() != 0:
        try:
            subprocess.check_call(['sudo', sys.executable] + sys.argv[1:])
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            print(f"{e}")
            sys.exit(1)

def start_ssh_tunnel(ssh_profile: str = ''):
    ssh_config = get_ssh_profile_details(ssh_profile)
    start_tunnel(ssh_config)

def show_help(parser):
    parser.print_help()
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Local Forwarding Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_ssh_profile = subparsers.add_parser("ssh-profile", help="Set default SSH profile")
    parser_ssh_profile.add_argument("profile", type=str, help="Profile name")

    parser_add = subparsers.add_parser("add", help="Add a new host")
    parser_add.add_argument("host", type=str, help="Host to add")

    parser_start = subparsers.add_parser("start", help="Start the SSH tunnel")
    parser_start.add_argument("profile", type=str, nargs="?", default=None, help="SSH profile to use")

    subparsers.add_parser("logs", help="Show SSH tunnel logs")
    subparsers.add_parser("stop", help="Stop the SSH tunnel")

    parser_help = subparsers.add_parser("help", help="Show help information")
    parser_help.set_defaults(func=lambda args: show_help(parser))

    args = parser.parse_args()
    
    if args.command == "add":
        ensure_sudo()
        add_host(args.host)
    elif args.command == "start":
        ensure_sudo()
        start_ssh_tunnel(args.profile)
    elif args.command == "logs":
        ensure_sudo()
        show_logs()
    elif args.command == "stop":
        ensure_sudo()
        stop_tunnel()
    elif args.command == "ssh-profile":
        set_default_profile(args.profile)
    elif args.command == "help":
        show_help(parser)
    else:
        parser.print_help()
        sys.exit(1)



if __name__ == '__main__':
    main()
