#!/usr/bin/env python3
import zono.colorlogger
import zono.settings
import parser_util
import subprocess
import argparse
import plistlib
import colorama
import tabulate
import logging
import shutil
import json
import sys
import os


logger = zono.colorlogger.create_logger("service")


def get_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


settings = zono.settings.Settings(
    get_file("settings.json"), {"domain": (str, None, "com.kareem.services")}
)


def get_service_line(job_label):
    try:
        launchctl_output = subprocess.check_output(["launchctl", "list"], text=True)

        lines = launchctl_output.strip().split("\n")
        for line in lines:
            if job_label in line:
                return line

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running launchctl list: {e}")
        return None


def get_service(opts, parser):
    with open(get_file("services.json"), "r") as f:
        services = json.load(f)

    service = services.get(opts.service, None)
    if service is None:
        return parser.error(f"Service {opts.service} does not exist")

    return service, services


def get_domain():
    return f"gui/{os.getuid()}"


def get_plist_data(plist_path):
    required_keys = [
        "Label",
        "Program",
        "RunAtLoad",
        "StandardOutPath",
        "StandardErrorPath",
        "WorkingDirectory",
    ]

    with open(plist_path, "rb") as plist_file:
        plist_data = plistlib.load(plist_file)

        for key in required_keys:
            if key not in plist_data:
                return [key]

        return plist_data


def get_service_target(service):
    return f"{get_domain()}/{get_job_label(service)}"


def get_job_label(service_name):
    file = get_file(os.path.join(".services", f"{service_name}.plist"))
    if not os.path.exists(file):
        return f'{settings.get_value("domain")}.{service_name}'
    with open(file, "rb") as f:
        return plistlib.load(f).get("Label", None)


def service_status(service):
    job_label = get_job_label(service)
    status = get_service_line(job_label)
    if status is None:
        return None, None, None
    pid, retcode, name = status.split("\t")
    if pid == "-":
        return False, None, int(retcode)

    return True, int(pid), int(retcode)


def str_stat(status):
    status = list(status)
    status[1] = str(status[1])
    status[2] = str(status[2])
    if status[0] is None:
        return ["None"] * 3
    elif status[0] is True:
        return (
            f"{colorama.Fore.GREEN}Running{colorama.Fore.RESET}",
            status[1],
            status[2],
        )

    elif status[0] is False:
        return (
            f"{colorama.Fore.RED}Stopped{colorama.Fore.RESET}",
            status[1],
            status[2],
        )

    else:
        raise Exception("Invalid service status")


def create_service_config(entry_point, service_name, domain):
    with open(get_file("services.plist"), "r") as f:
        return (
            f.read()
            .replace("{SERVICE_NAME}", service_name)
            .replace("{PATH_TO_PROGRAM}", entry_point)
            .replace("{WORKING_DIR}", os.path.dirname(entry_point))
            .replace("{DOMAIN}", domain)
            .replace("{LAUNCHER_PATH}", get_file("service_launcher.py"))
        )


def kickstart_service(service):
    c = subprocess.run(
        [
            "launchctl",
            "kickstart",
            "-k",
            get_service_target(service),
        ]
    )
    if c.returncode == 0:
        logger.info("Service successfully started")
        return 0
    else:
        logger.error("Failed to launch service")
        return 1


def create_service(service, config):
    logger.debug("Service not found registering with launchctl")
    c = subprocess.run(["launchctl", "enable", get_service_target(service)])
    if c.returncode != 0:
        logger.error("Failed to launch service")
        logger.debug("error while enabling the service")
        return 1
    logger.debug("Enabled the service")
    c = subprocess.run(["launchctl", "bootstrap", get_domain(), config])

    if c.returncode != 0:
        logger.error("Failed to launch service")
        logger.debug("error while enabling the service")
        return 1
    logger.debug("Added service")
    logger.info("Service started successfully")
    return 0


def kill_service(service):
    c = subprocess.run(["launchctl", "kill", "9", get_service_target(service)])
    if c.returncode != 0:
        logger.error("An error occurred while stopping the service")
        return 1
    logger.info("Service stopped successfully")
    return 0


def terminate_service(service):
    c = subprocess.run(["launchctl", "stop", get_job_label(service)])
    if c.returncode != 0:
        logger.error("An error occurred while stopping the service")
        return 1
    logger.info("Service stopped successfully")
    return 0


def stop_service(service, kill=False):
    stat, *_ = service_status(service)
    if stat is not True:
        logger.error(f"Service {service} is already stopped")
        return 1
    if kill:
        return kill_service(service)
    else:
        return terminate_service(service)


def start_service(service, opts):
    config_path = get_file(f'.services/{service["name"]}.plist')
    if not os.path.exists(config_path):
        logger.debug("Service config file not found creating a new one")
        with open(config_path, "w") as f:
            f.write(
                create_service_config(
                    service["mainfile"], service["name"], settings.get_value("domain")
                )
            )

    status = service_status(service["name"])[0]
    if status is True:
        if opts.force:
            logger.info("Restarting the service")
            return kickstart_service(service["name"])
        else:
            logger.error(
                "Service is already running use --force to start the service anyways"
            )
    elif status is False:
        logger.debug("Starting the service")
        return kickstart_service(service["name"])
    elif status is None:
        return create_service(service["name"], config_path)


def remove_service(service):
    stat, *_ = service_status(service)
    if stat is None:
        logger.error(f"Service {service} is already removed")
        return 1

    config = get_file(f".services/{service}.plist")
    c = subprocess.run(["launchctl", "disable", get_service_target(service)])
    if c.returncode != 0:
        logger.info("error while disabling the service")
    else:
        logger.debug("Disabled the service")
    c = subprocess.run(["launchctl", "bootout", get_domain(), config])

    if c.returncode != 0:
        logger.info("Failed to remove the service")
        logger.debug("error while booting out the service")
        return 1

    logger.info("Service removed successfully")
    return 0


def get_service_info(service, service_info):
    outpath = os.path.join(os.path.dirname(service_info["mainfile"]), ".output/stdout")
    outpath = outpath if os.path.exists(outpath) else None
    config_file = (
        get_file(f".services/{service}.plist")
        if os.path.exists(get_file(f".services/{service}.plist"))
        else None
    )

    stat, pid, retcode = service_status(service)
    return dict(
        status=stat,
        pid=pid,
        return_code=retcode,
        job_label=get_job_label(service),
        domain=get_domain(),
        service_target=get_service_target(service),
        config_file=config_file,
        output_file=outpath,
        startup=service_info.get("startup", False),
        mainfile=service_info.get("mainfile"),
    )


def start(opts, parser):
    with open(get_file("services.json"), "r") as f:
        services = json.load(f)

    if opts.service == "all":
        for service, info in services.items():
            info["name"] = service
            start_service(info, opts)

        return 0
    service = services.get(opts.service, None)
    if service is None:
        return parser.error(f"Service {opts.service} does not exist")
    service["name"] = opts.service
    code = start_service(service, opts)
    if code != 0:
        return code

    if opts.watch:
        outpath = os.path.join(os.path.dirname(service["mainfile"]), ".output/stdout")
        if os.path.exists(outpath) is not True:
            logger.error("Output file for the service does not exist")
            return 1
        os.system(f"tail -f {outpath}")


def status(opts, parser):
    with open(get_file("services.json"), "r") as f:
        services = json.load(f)

    headers = ["Name", "Status", "PID", "Return Code"]
    if opts.json is True:
        services_status = dict()
        for service, service_info in services.items():
            services_status[service] = get_service_info(service, service_info)
        print(json.dumps(services_status, indent=4))
    else:
        data = [
            [service, *str_stat(service_status(service))] for service in services.keys()
        ]
        print(tabulate.tabulate(data, headers=headers, tablefmt="simple_grid"))
    return 0


def logs(opts, parser):
    service, _ = get_service(opts, parser)

    outpath = os.path.join(os.path.dirname(service["mainfile"]), ".output/stdout")
    if os.path.exists(outpath) is not True:
        logger.error("Output file for the service does not exist")
        return 1
    if opts.watch is True:
        if service_status(opts.service)[0] is True:
            os.system(f"tail -f {outpath}")
            return 0
        logger.info("Service is not running displaying previous logs")
    elif opts.file is True:
        print(outpath)
        return 0

    elif opts.clear:
        with open(outpath, "w") as f:
            f.write("")
        logger.info("Cleared log file successfully")
        return 0
    with open(outpath, "r") as f:
        if opts.json:
            print(json.dumps(f.readlines(), indent=4))
        else:
            g = f.read()
            if g:
                print(g)
    return 0


def stop(opts, parser):
    with open(get_file("services.json"), "r") as f:
        services = json.load(f)

    if opts.service == "all":
        for service in services:
            stop_service(service, kill=opts.kill)
        return 0
    service = services.get(opts.service, None)
    if service is None:
        return parser.error(f"Service {opts.service} does not exist")
    if opts.remove:
        return remove_service(
            opts.service,
        )
    return stop_service(opts.service, kill=opts.kill)


def unload(opts, parser):
    _, services = get_service(opts, parser)

    remove_service(opts.service)
    services.pop(opts.service)
    with open(get_file("services.json"), "w") as f:
        json.dump(services, f, indent=4)

    os.remove(get_file(f".services/{opts.service}.plist"))


def info(opts, parser):
    service, _ = get_service(opts, parser)

    service_info = get_service_info(opts.service, service)
    if opts.json:
        print(json.dumps(service_info, indent=4))
        return 0

    stat, pid, retcode = str_stat(
        (service_info["status"], service_info["pid"], service_info["return_code"])
    )
    service_info["status"] = stat
    service_info["pid"] = pid
    service_info["return_code"] = retcode
    service_info["config_file"] = service_info["config_file"] or "None"
    service_info["output_file"] = service_info["output_file"] or "None"
    table_data = [[key, value] for key, value in service_info.items()]

    print(
        tabulate.tabulate(table_data, headers=["Key", "Value"], tablefmt="simple_grid")
    )


def create_plist(opts, parser):
    opts.input_file = os.path.abspath(opts.input_file)
    if not os.path.exists(opts.input_file):
        return parser.error(f"File {opts.input_file} does not exist")

    config = create_service_config(opts.input_file, opts.service_name, opts.domain)
    if opts.output:
        with open(opts.output, "w") as f:
            f.write(config)
    else:
        print(config)

    return 0


def load(opts, parser):
    opts.inputfile = opts.file
    opts.file = os.path.abspath(opts.file)
    if not os.path.exists(opts.file):
        return parser.error(f"File {opts.inputfile} does not exist")

    if os.path.splitext(opts.file)[1] == ".plist":
        data = get_plist_data(opts.file)
        if isinstance(data, list):
            return parser.error(
                f"Invalid plist file missing required attribute {data[0]}"
            )

        workdir = data["WorkingDirectory"]
        mainfile = os.path.join(workdir, data["Label"])

        service_domain = data["Label"].split(".")
        service_name = service_domain.pop()
        service_domain = ".".join(service_domain)
        if settings.get_value("domain") != service_domain:
            service_name = data["Label"]

        service_name = opts.name or service_name

        with open(get_file("services.json")) as f:
            services = json.load(f)
        if service_name in services:
            return parser.error("Service already exists")
        services[service_name] = dict(mainfile=mainfile, startup=False)
        with open(get_file("services.json"), "w") as f:
            json.dump(services, f, indent=4)
        if os.path.dirname(opts.file) != get_file(".services"):
            shutil.copy(opts.file, get_file(".services"))
            new_path = os.path.join(get_file(".services"), f"{service_name}.plist")
            os.rename(
                os.path.join(get_file(".services"), os.path.basename(opts.file)),
                new_path,
            )
    else:
        if opts.name is None:
            return parser.error("Missing name for the service specify name using -name")
        with open(get_file("services.json")) as f:
            services = json.load(f)
        services[opts.name] = dict(mainfile=opts.file, startup=False)
        with open(get_file("services.json"), "w") as f:
            json.dump(services, f, indent=4)
    return 0


def help(opts, parser):
    parser.main_parser.print_help()
    return 0


commands = dict(
    start=start,
    status=status,
    stop=stop,
    logs=logs,
    load=load,
    unload=unload,
    info=info,
    create_plist=create_plist,
    help=help,
)


def create_start_parser(subparser):
    start_parser = subparser.add_parser("start", help="Starts a service")
    start_parser.add_argument(
        "service", help="The name of the service you want to start"
    )
    start_parser.add_argument(
        "--force",
        help="Starts the service even if it is already running",
        action="store_true",
    )
    start_parser.add_argument(
        "--watch",
        help="Prints live logs from the specified service after it is started",
        action="store_true",
    )


def create_status_parser(subparser):
    status_parser = subparser.add_parser(
        "status", help="View the status of all services"
    )
    status_parser.add_argument(
        "--json", help="Outputs service status as json", action="store_true"
    )


def create_stop_parser(subparser):
    stop_parser = subparser.add_parser("stop", help="Stops the specified service")
    stop_parser.add_argument("service", help="The name of the service you want to stop")
    stop_group = stop_parser.add_mutually_exclusive_group()
    stop_group.add_argument(
        "--remove",
        help="Stop and then unload the specified service",
        action="store_true",
    )
    stop_group.add_argument(
        "--kill", help="Force kill the service", action="store_true"
    )


def create_log_parser(subparser):
    logs_parser = subparser.add_parser(
        "logs",
        help="Prints the logs from the specified service",
        description="Prints the logs from the specified service",
    )
    logs_parser.add_argument("service", help="The name of the service you want to stop")
    g = logs_parser.add_mutually_exclusive_group()
    g.add_argument(
        "--watch",
        help="Prints live logs from the specified service",
        action="store_true",
    )
    g.add_argument(
        "--file",
        help="Displays the path to the log file",
        action="store_true",
    )
    g.add_argument(
        "--clear",
        help="Clear the log file",
        action="store_true",
    )
    logs_parser.add_argument("--json", help="Outputs logs as json", action="store_true")


def create_load_parser(subparser):
    load_parser = subparser.add_parser(
        "load", help="Load a .plist or script in to the service manager as service"
    )
    load_parser.add_argument("file", help="The file you would like to load")
    load_parser.add_argument(
        "-name", help="The name of the service you would like to load", default=None
    )


def create_unload_parser(subparser):
    unload_parser = subparser.add_parser(
        "unload", help="Unloads a service from the service manager"
    )
    unload_parser.add_argument(
        "service", help="The name of the service you want to unregister"
    )


def create_info_parser(subparser):
    info_parser = subparser.add_parser(
        "info", help="Display information about a service"
    )
    info_parser.add_argument(
        "--json", help="Displays the service info as json", action="store_true"
    )
    info_parser.add_argument("service", help="Name of the service you want to view")


def create_plist_parser(subparser):
    create_plist_parser = subparser.add_parser(
        "create_plist",
        help="Create a plist configuration file for a certain script",
    )
    create_plist_parser.add_argument(
        "input_file", help="The file the service should run"
    )
    create_plist_parser.add_argument("service_name", help="The name of the service")
    create_plist_parser.add_argument(
        "--domain",
        help="Manually set the domain that the service uses",
        default=settings.get_value("domain"),
    )
    create_plist_parser.add_argument(
        "--output",
        "-o",
        help="The file you would like to output the plist in to",
        default=None,
    )


def create_help_parser(subparser):
    subparser.add_parser("help", help="Display command help")


def parse_args():
    parser = argparse.ArgumentParser(
        prog="service",
        description="A simple service manager",
        formatter_class=parser_util.NoSubparsersMetavarFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity level (up to 2 times)",
    )

    subparser = parser.add_subparsers(title="Commands", dest="command", required=True)
    create_start_parser(subparser)
    create_stop_parser(subparser)
    create_plist_parser(subparser)
    create_load_parser(subparser)
    create_log_parser(subparser)
    create_unload_parser(subparser)
    create_info_parser(subparser)
    create_status_parser(subparser)
    create_help_parser(subparser)

    opts = parser.parse_args()
    verbosity = min(2, opts.verbose)
    log_levels = [
        logging.ERROR,
        logging.INFO,
        logging.DEBUG,
    ]
    log_level = log_levels[verbosity]
    logger.setLevel(log_level)

    chosen_parser = subparser.choices[opts.command]
    chosen_parser.main_parser = parser
    return (opts, chosen_parser)


def main():
    opts, parser = parse_args()
    if not os.path.exists(get_file("env.txt")):
        import install

        install.logger.setLevel(logger.getEffectiveLevel())
        install.main()

    with open(get_file("env.txt"), "w") as f:
        f.write(os.environ.get("PATH"))
    if os.getuid() == 0:
        parser.error(
            "To manage user services the command needs to be run as a non-root"
        )

    cmd = commands.get(opts.command)
    sys.exit(cmd(opts, parser))


if __name__ == "__main__":
    main()
