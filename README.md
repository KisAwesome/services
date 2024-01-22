# services

A simple macos service manager

# Service Manager Documentation

## Introduction

The Service Manager is a simple command-line tool designed for managing services. It provides various commands to start, stop, load, unload, and gather information about services. Additionally, it supports functionalities like viewing service status and logs.

## Command-Line Interface

### `service start`

Starts a service.

- **Arguments:**
  - `service`: The name of the service to start.
- **Options:**
  - `--force`: Starts the service even if it is already running.
  - `--watch`: Prints live logs from the specified service after it is started.

### `service status`

View the status of all services.

- **Options:**
  - `--json`: Outputs service status as JSON.

### `service stop`

Stops the specified service.

- **Arguments:**

  - `service`: The name of the service to stop.

- **Options:**
  - `--remove`: Stop and then unload the specified service.
  - `--kill`: Forcefully kill the service.

### `service logs`

Prints the logs from the specified service.

- **Arguments:**

  - `service`: The name of the service to view logs.

- **Options:**
  - `--watch`: Prints live logs from the specified service.
  - `--file`: Displays the path to the log file.
  - `--clear`: Clear the log file.
  - `--json`: Outputs logs as JSON.

### `service load`

Load a `.plist` or script into the service manager as a service.

- **Arguments:**

  - `file`: The file you would like to load.

- **Options:**
  - `-name`: The name of the service you would like to load (default: None).

### `service unload`

Unloads a service from the service manager.

- **Arguments:**
  - `service`: The name of the service to unregister.

### `service info`

Display information about a service.

- **Arguments:**

  - `service`: Name of the service you want to view.

- **Options:**
  - `--json`: Displays the service info as JSON.

### `service create_plist`

Create a plist configuration file for a certain script.

- **Arguments:**

  - `input_file`: The file the service should run.
  - `service_name`: The name of the service.

- **Options:**
  - `--domain`: Manually set the domain that the service uses (default: value from settings).
  - `--output`, `-o`: The file you would like to output the plist into (default: None).

### `service help`

Display command help.

## Global Options

- `-v`, `--verbose`: Increase verbosity level (up to 2 times).

## Examples

### Starting a Service

```bash
service start my_service
```

### Viewing Service Status

```bash
service status
```

### Stopping a Service

```bash
service stop my_service --remove
```

### Viewing Service Logs

```bash
service logs my_service --watch
```

### Loading a Service

```bash
service load my_script.sh -name my_custom_service
```

### Unloading a Service

```bash
service unload my_custom_service
```

### Displaying Service Information

```bash
service info my_service --json
```

### Creating a Plist Configuration

```bash
service create_plist my_script.sh my_custom_service --output my_custom_service.plist
```

## Verbose Mode

To increase verbosity, use the `-v` or `--verbose` option. The level can be increased up to 2 times for more detailed output.

---

**Note:** This documentation assumes that you have the necessary permissions and knowledge to manage services on your system. Always exercise caution when interacting with services.
