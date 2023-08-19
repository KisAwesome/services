#!/Library/Frameworks/Python.framework/Versions/3.11/bin/python3
import subprocess
import sys
import os


def get_file(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def main():
    print("fff")
    sys.argv.pop(0)
    path = " ".join(sys.argv)

    with open(get_file("env.txt"), "r") as f:
        PATH = f.read()

    os.environ["PATH"] = PATH
    cmd = [sys.executable, "/Users/kareem/Documents/dev/Python/Apps/run/main.py", path]

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
