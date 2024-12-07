import paramiko
import time


def check_postgres_status():
    # SSH connection details
    hostname = "194-36-88-187.cloud-xip.com"
    username = "root"
    password = "KAM2024kam2024"
    port = 22

    try:
        # Initialize SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        print(f"Connecting to {hostname}...")
        ssh.connect(hostname, port, username, password)
        print("Successfully connected via SSH")

        # Commands to check PostgreSQL status
        commands = [
            "systemctl status postgresql || service postgresql status",  # Try both systemctl and service
            "ps aux | grep postgres",  # Check running postgres processes
            "netstat -tuln | grep 5432",  # Check if postgres is listening
            "cat /etc/postgresql/*/main/postgresql.conf | grep listen_addresses",  # Check listen addresses
            "cat /etc/postgresql/*/main/pg_hba.conf",  # Check connection permissions
        ]

        for command in commands:
            print(f"\nExecuting: {command}")
            stdin, stdout, stderr = ssh.exec_command(command)

            # Print output
            output = stdout.read().decode()
            error = stderr.read().decode()

            if output:
                print("Output:")
                print(output)
            if error:
                print("Error:")
                print(error)

    except Exception as e:
        print(f"Error: {str(e)}")

    finally:
        if "ssh" in locals():
            ssh.close()
            print("\nSSH connection closed")


if __name__ == "__main__":
    check_postgres_status()
