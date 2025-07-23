import subprocess


def get_battery_status():
    try:
        output = subprocess.check_output(["acpi", "-b"]).decode("utf-8")
        battery_percentage = output.split(",")[1].strip().replace("%", "")

        return battery_percentage
    except subprocess.CalledProcessError as e:
        return f"Error retrieving battery status: {e}"
    except FileNotFoundError:
        return "The 'acpi' command is not available on this system."
