import zono.colorlogger as cl
import main as lib
import shutil
import json
import os


def get_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def main():
    outfile = "com.kareem.services.startup.plist"

    with open(get_file("services.json"), "w") as f:
        json.dump({}, f)

    os.system(f'chmod +x {get_file("service_launcher.py")}')
    if not os.path.exists(get_file(".services")):
        os.mkdir(get_file(".services"))

    config = lib.create_service_config("startup.py", "startup", "com.kareem.services")
    with open(outfile, "w") as f:
        f.write(config)
    shutil.move(
        os.path.abspath(outfile),
        os.path.join(
            os.path.expanduser("~/Library/LaunchAgents/"), os.path.basename(outfile)
        ),
    )
    cl.log("Installed successfully")


if __name__ == "__main__":
    main()
