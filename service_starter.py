import subprocess
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def run_command(command):
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e}")
        logging.error(f"Error output: {e.stderr}")
        return None


def is_service_running(service_name):
    status = run_command(["sudo", "service", service_name, "status"])
    return status is not None and "active (running)" in status


def start_service(service_name):
    if not is_service_running(service_name):
        logging.info(f"{service_name} is not running. Starting it now...")
        result = run_command(["sudo", "service", service_name, "start"])
        if result is not None:
            logging.info(f"{service_name} started successfully.")
        else:
            logging.error(f"Failed to start {service_name}.")
    else:
        logging.info(f"{service_name} is already running.")


def main():
    # Check and start PostgreSQL
    start_service("postgresql")

    # Check and start Redis
    start_service("redis-server")

    # Your existing main code goes here
    # For example:
    # from your_module import your_main_function
    # your_main_function()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        logging.error(
            "This script is intended for Unix-like systems. It may not work correctly on Windows."
        )
    else:
        main()
