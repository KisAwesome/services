import zono.colorlogger as cl
import main as lib
import json
import os


def get_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


logger = cl.create_logger("installer", 0)


def main():
    logger.important_log("Installing service because this is the first run")
    outfile = "com.kareem.services.startup.plist"

    if not os.path.exists(get_file("services.json")):
        with open(get_file("services.json"), "w") as f:
            json.dump({}, f)

    os.system(f'chmod +x {get_file("service_launcher.py")}')
    if not os.path.exists(get_file(".services")):
        os.mkdir(get_file(".services"))

    config = lib.create_service_config("startup.py", "startup", "com.kareem.services")
    logger.debug("Created startup service file")
    with open(
        os.path.join(
            os.path.expanduser("~/Library/LaunchAgents/"), os.path.basename(outfile)
        ),
        "w",
    ) as f:
        f.write(config)
    logger.debug("Added startup service file to ~/Library/LaunchAgents")
    logger.important_log("Installed successfully")


if __name__ == "__main__":
    main()
