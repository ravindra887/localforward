# Local Forwarding Utility

A command-line tool to manage SSH tunnels and local forwarding.

## Installation

### Prerequisites
- Linux or macOS system

### Steps
1. Run the following command to install the utility from the binary:
   ```sh
   curl -fsSL https://github.com/ravindra887/localforward/raw/main/install.sh | bash
   ```

## Usage

Run the script using:
```sh
localforward <command> [options]
```

### Commands

#### 1. Set Default SSH Profile
```sh
localforward ssh-profile <profile_name>
```
Sets the default SSH profile.

#### 2. Add a New Host
```sh
localforward add <host>
```
Adds a new host for forwarding.

#### 3. Start SSH Tunnel
```sh
localforward start [profile_name]
```
Starts an SSH tunnel using the specified profile. If no profile is provided, the default profile is used.

#### 4. Show SSH Tunnel Logs
```sh
localforward logs
```
Displays SSH tunnel logs.

#### 5. Stop SSH Tunnel
```sh
localforward stop
```
Stops the running SSH tunnel.

#### 6. Show Help Information
```sh
localforward help
```
Displays help information about the available commands.

## License
This project is licensed under the MIT License.

## Contributing
Feel free to submit pull requests or open issues for improvements!

