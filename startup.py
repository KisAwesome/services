#!/usr/bin/env python3
import main as lib
import json
import os


def get_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


class Force:
    force = True


def main():
    print("Loading startup services")
    with open(get_file("services.json"), "r") as f:
        services = json.load(f)
    for service, info in services.items():
        if info.get("startup", False) is True:
            info["name"] = service
            lib.start_service(info, Force)

    print("Loaded startup services")


if __name__ == "__main__":
    main()
