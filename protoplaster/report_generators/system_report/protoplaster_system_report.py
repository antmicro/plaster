#!/usr/bin/env python3
import subprocess
import argparse
import zipfile
from dataclasses import dataclass
import yaml
import os
import sys
from jinja2 import Environment, DictLoader
import shutil
import threading
import itertools

CLEAR_LINE = "\033[2K"


class SummaryConfig:

    def __init__(self, config):
        if "title" in config and "run" in config:
            self.title = config["title"]
            self.script = config["run"]
        else:
            print("Error: summary config is incomplete")
            sys.exit(1)


class CommandConfig:

    def __init__(self, yaml_config):
        name, config = yaml_config
        required_fields_present = "run" in config and "output" in config
        superuser_correct = "superuser" not in config or config[
            "superuser"] in ["required", "preferred"]
        if not required_fields_present or not superuser_correct:
            print(f"Error: {name} config is invalid")
            sys.exit(1)
        self.name = name
        self.script = config["run"]
        if "superuser" in config and not is_root():
            if config["superuser"] == "required":
                print(
                    f"Error: You have insufficient permissions to run {self.script}. No system report will be generated."
                )
                sys.exit(1)
            else:
                print(
                    f"Warning: You have insufficient permissions to run {self.script}. Output from this command will be skipped in the system report."
                )
        self.summary_configs = [
            SummaryConfig(c) for c in config.get("summary", [])
        ]
        self.output_file = config.get("output", None)
        self.on_fail = CommandConfig(
            (name, config["on-fail"])) if "on-fail" in config else None


@dataclass
class SubReportSummary:
    title: str
    content: str


@dataclass
class SubReportResult:
    name: str
    raw_output: str
    output_file: str
    summaries: list[SubReportSummary]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o",
                        "--output-file",
                        type=str,
                        help="Path to the output file",
                        default="report.zip")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to the yaml config file",
        default=f"{os.path.dirname(__file__)}/default_commands.yml")
    parser.add_argument("--sudo", action='store_true', help="Run as sudo")
    return parser.parse_args()


def generate_html(sub_reports):
    with open(f"{os.path.dirname(__file__)}/report_template.html"
              ) as template_file:
        html_template = template_file.read()
    environment = Environment(
        loader=DictLoader({"report_template": html_template}))
    template = environment.get_template("report_template")
    return template.render(sub_reports=sub_reports)


def read_config(filename):
    with open(filename) as file:
        return yaml.safe_load(file)


def read_commands(filename):
    command_configs = []
    for config in read_config(filename).items():
        command_configs.append(CommandConfig(config))
    return command_configs


def get_cmd_output(cmd):
    return subprocess.check_output(cmd,
                                   shell=True,
                                   text=True,
                                   stderr=subprocess.STDOUT)


def is_root():
    return int(get_cmd_output("id -u")) == 0


def run_command(config):
    try:
        out = get_cmd_output(f"sh -c '{config.script}'")
        summaries = []
        for summary_config in config.summary_configs:
            try:
                summary_content = subprocess.check_output(
                    f"sh -c '{summary_config.script}'",
                    shell=True,
                    text=True,
                    stderr=subprocess.STDOUT,
                    env=os.environ | {
                        "PROTOPLASTER_SCRIPTS":
                        f"{os.path.dirname(__file__)}/scripts"
                    },
                    input=out)
                summaries.append(
                    SubReportSummary(summary_config.title, summary_content))
            except:
                summaries.append(
                    SubReportSummary(summary_config.title,
                                     "this summary is empty"))
        return SubReportResult(config.name, out, config.output_file, summaries)
    except:
        if config.on_fail:
            return run_command(config.on_fail)
        return None


spinner_frames = ["   ", ".  ", ".. ", "..."]


def generate_system_report(config_path):
    command_configs = read_commands(config_path)

    files = []

    sub_reports = []
    for config in command_configs:
        sub_report = None
        finish_event = threading.Event()

        def run():
            nonlocal sub_report
            sub_report = run_command(config)
            finish_event.set()

        thrd = threading.Thread(target=run)
        print(f"running {config.name}", end="")
        thrd.start()
        for spinner_frame in itertools.cycle(spinner_frames):
            if finish_event.wait(0.5):
                break
            print(f"\r{CLEAR_LINE}running {config.name}{spinner_frame}",
                  end="")

        if sub_report:
            sub_reports.append(sub_report)
            if config.output_file:
                files.append((config.output_file, sub_report.raw_output))
            print(f"\r{CLEAR_LINE}{config.name} completed")
        else:
            print(f"\r{CLEAR_LINE}{config.name} failed")

    files.append(("system_report_summary.html", generate_html(sub_reports)))

    # apart from html file we have to put in the archive style.css and all additional files stored in static/
    with open(f"{os.path.dirname(__file__)}/style.css", "r") as style:
        files.append(("style.css", style.read()))

    def read_files_from_dir(dir, dest):
        for root, dirs, files in os.walk(dir):
            for file in files:
                with open(os.path.join(dir, file), "r") as file_content:
                    dest.append((f"static/{file}", file_content.read()))
            for dirname in dirs:
                read_files_from_dir(os.path.join(root, dirname), dest)

    read_files_from_dir(f"{os.path.dirname(__file__)}/static", files)

    return files


def main():
    args = parse_args()

    if args.sudo:
        os.execv(shutil.which("sudo"),
                 [__file__] + list(filter(lambda a: a != "--sudo", sys.argv)))

    files = generate_system_report(args.config)

    with open(args.output_file, "wb") as archive_file:
        with zipfile.ZipFile(archive_file, 'w',
                             zipfile.ZIP_DEFLATED) as archive:
            for filename, content in files:
                archive.writestr(filename, content)


if __name__ == "__main__":
    main()
