import collections
import os
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml


class ComplexityMode(Enum):
    NUMBER_OF_LINES = "Number of lines"
    LEFT_WHITE_SPACES = "Left white spaces"


class ChangesMode(Enum):
    NUMBER_OF_COMMITS = "Number of commits"
    TOTAL_LINES_CHANGED = "Total lines changed in all commits"


class Hotspots:
    def __init__(self,
                 repo_path: str,
                 complexity_method: ComplexityMode = ComplexityMode.NUMBER_OF_LINES,
                 changes_method: ChangesMode = ChangesMode.NUMBER_OF_COMMITS,
                 months_back: int = -1):

        self.repo_path = repo_path
        self.complexity_method = complexity_method
        self.changes_method = changes_method
        self.months_back = months_back

        self.config = self.read_config()
        self.data = pd.DataFrame()

    @staticmethod
    def read_config(config_path: str = "config/hotspots.yaml") -> dict:
        with open(Path(config_path)) as f:
            config = yaml.safe_load(f)
        return config

    def get_files(self) -> None:
        file_paths = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.config["exclude_dirs"]]
            for file in files:
                if file in self.config["exclude_files"]:
                    continue
                file_paths.append(Path(root) / file)
        self.data = pd.DataFrame(file_paths, columns=["file_path"])

    def get_complexity(self) -> None:
        match self.complexity_method:
            case ComplexityMode.NUMBER_OF_LINES:
                self._get_number_of_lines()
            case ComplexityMode.LEFT_WHITE_SPACES:
                self._get_left_white_spaces()
            case _:
                raise ValueError(f"ERROR: Mode {self.complexity_method} does not apply to complexity")

    def get_changes(self) -> None:
        match self.changes_method:
            case ChangesMode.NUMBER_OF_COMMITS:
                self._get_number_of_commits()
            case ChangesMode.TOTAL_LINES_CHANGED:
                self._get_total_lines_changed()
            case _:
                raise ValueError(f"ERROR: Mode {self.changes_method} does not apply to changes")

    def _get_number_of_lines(self) -> None:
        self.data["complexity"] = self.data['file_path'].apply(lambda x: self._count_file_lines(x))

    @staticmethod
    def _count_file_lines(file_path) -> int:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return len(file.readlines())

    def _get_left_white_spaces(self) -> None:
        self.data["complexity"] = self.data['file_path'].apply(lambda x: self._count_file_left_white_spaces(x))

    @staticmethod
    def _count_file_left_white_spaces(file_path: str) -> int:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            total_white_spaces = 0
            for line in file:
                stripped_line = line.lstrip()
                if stripped_line and not stripped_line.startswith(('#', '//', '/*', '*')):
                    total_white_spaces += len(line) - len(stripped_line)
        return total_white_spaces

    def _get_number_of_commits(self) -> None:
        command = self._get_number_of_commits_command()
        output = self._run_command(command)
        files = output.split('\n')
        counts = collections.Counter(files)
        del counts['']  # Remove empty string key which comes from extra newlines

        # Map the commit counts to the 'changes' column in the data DataFrame
        self.data['changes'] = self.data['file_path'].apply(lambda x: counts[os.path.relpath(x, start=self.repo_path)])

    def _get_number_of_commits_command(self) -> list:
        command = [
            'git', '-C', self.repo_path,
            'log',
            '--pretty=format:', '--name-only', '--', '.'
        ]

        if self.months_back != -1:
            since_date = (datetime.now() - timedelta(days=30 * self.months_back)).strftime('%Y-%m-%d')
            command.insert(4, f'--since={since_date}')

        return command

    def _get_total_lines_changed(self) -> None:
        self.data["changes"] = self.data['file_path'].apply(lambda x: self._count_file_total_lines_changed(x))

    def _count_file_total_lines_changed(self, file_path: str) -> int:
        rel_path = os.path.relpath(file_path, start=self.repo_path)
        command = self._get_lines_changed_command(rel_path)
        output = self._run_command(command)
        changes = [line.split('\t')[:2] for line in output.split('\n') if line]
        total_changes = sum(int(additions) + int(deletions) for additions, deletions in changes)
        return total_changes

    def _get_lines_changed_command(self, rel_path: str) -> list:
        command = [
            'git', '-C', self.repo_path,
            'log',
            '--numstat',
            '--pretty=format:',
            '--', rel_path
        ]

        if self.months_back != -1:
            since_date = (datetime.now() - timedelta(days=30 * self.months_back)).strftime('%Y-%m-%d')
            command.insert(4, f'--since={since_date}')

        return command

    @staticmethod
    def _run_command(command: list) -> str:
        try:
            return subprocess.check_output(command).decode('utf-8').strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command failed with error: {e}")

    def get_color(self) -> None:
        def color_for_file(file_path: str) -> str:
            file_path_str = str(file_path)
            if file_path_str.endswith('.yaml'):
                return 'red'
            elif file_path_str.endswith('.py'):
                return 'blue'
            else:
                return 'grey'

        def legend_label(file_path: str) -> str:
            file_path_str = str(file_path)
            if file_path_str.endswith('.yaml'):
                return '.yaml'
            elif file_path_str.endswith('.py'):
                return '.py'
            else:
                return 'other'

        self.data['color'] = self.data['file_path'].apply(color_for_file)
        self.data['legend'] = self.data['file_path'].apply(legend_label)

    def plot_data(self) -> None:
        self.get_color()
        self.data['file'] = self.data['file_path'].apply(lambda x: str(Path(x).relative_to(self.repo_path)))
        fig = px.scatter(
            self.data,
            x='changes',
            y='complexity',
            hover_name='file',
            color='legend',  # Use the legend_label column for color
            hover_data={'complexity': False, 'changes': False, 'legend': False},
            title='Complexity vs Changes',
            labels={
                "complexity": f"Complexity - {self.complexity_method.value}",
                "changes": f"Changes - {self.changes_method.value}"
            },
            color_discrete_map={
                '.yaml': 'red',
                '.py': 'blue',
                'other': 'grey'
            }
        )
        fig.show()


if __name__ == "__main__":
    repo_path = "/Users/jabia/Git/aily-ai-fin"
    hotspots = Hotspots(repo_path,
                        complexity_method=ComplexityMode.LEFT_WHITE_SPACES,
                        changes_method=ChangesMode.TOTAL_LINES_CHANGED)
    hotspots.get_files()
    hotspots.get_complexity()
    hotspots.get_changes()
    hotspots.plot_data()
