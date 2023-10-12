from pathlib import Path
import plotly.express as px
import pandas as pd

from prettytable import PrettyTable
import subprocess
import os
import time
import yaml


def read_config() -> dict:
    with open(Path("config/hotspots.yaml")) as f:
        config = yaml.safe_load(f)
    return config


def get_file_lines(file_path) -> int:
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        return len(file.readlines())


def get_modification_frequency(file_path) -> int:
    result = subprocess.run(
        ['git', 'log', '--pretty=format:', '--name-only', f'--since="1 year ago"', file_path],
        text=True,
        capture_output=True
    )
    return len([line for line in result.stdout.split('\n') if line])


def analyze_repository(repo_path):
    config = read_config()
    exclude_dirs = config["exclude_dirs"]
    exclude_files = config["exclude_files"]
    os.chdir(repo_path)
    data = []

    complexity_time = 0
    mod_freq_time = 0

    for root, dirs, files in os.walk(repo_path):
        # Prevent os.walk from traversing into excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file in exclude_files:
                continue

            file_path = os.path.join(root, file)

            # Measure time taken to calculate complexity
            start_time = time.time()
            complexity = get_file_lines(file_path)
            complexity_time += time.time() - start_time

            # Measure time taken to calculate modification frequency
            start_time = time.time()
            mod_freq = get_modification_frequency(file_path)
            mod_freq_time += time.time() - start_time

            data.append((file_path, complexity, mod_freq))

    print(f"Total time for complexity calculations: {complexity_time:.2f} seconds")
    print(f"Total time for modification frequency calculations: {mod_freq_time:.2f} seconds")

    return data


def plot_data(data):
    # Convert data to a DataFrame for compatibility with Plotly Express
    df = pd.DataFrame(data, columns=["File", "Complexity", "Modification Frequency"])

    df['Shortened File'] = df['File'].apply(lambda x: os.path.relpath(x, start=repo_path))

    # Create the scatter plot using Plotly Express
    fig = px.scatter(
        df,
        x='Complexity',
        y='Modification Frequency',
        hover_name='Shortened File',  # This will show the file name when you hover over a point
        hover_data={'Complexity': False, 'Modification Frequency': False},
        title='Complexity vs Modification Frequency',
        labels={
            "Complexity": "Complexity (Lines of Code)",
            "Modification Frequency": "Modification Frequency (Past Year)"
        }
    )

    # Show the plot
    fig.show()


def print_most_complex_and_modified(data):
    # Sort data based on complexity and modification frequency
    sorted_by_complexity = sorted(data, key=lambda x: x[1], reverse=True)[:5]
    sorted_by_mod_freq = sorted(data, key=lambda x: x[2], reverse=True)[:5]

    # Create a table for the most complex files
    complexity_table = PrettyTable()
    complexity_table.field_names = ["File", "Complexity"]
    for item in sorted_by_complexity:
        complexity_table.add_row([item[0], item[1]])

    # Create a table for the most modified files
    mod_freq_table = PrettyTable()
    mod_freq_table.field_names = ["File", "Modification Frequency"]
    for item in sorted_by_mod_freq:
        mod_freq_table.add_row([item[0], item[2]])

    # Print the tables
    print(f"Top 5 Most Complex Files:\n{complexity_table}")
    print(f"\nTop 5 Most Modified Files:\n{mod_freq_table}")


if __name__ == "__main__":
    repo_path = "/Users/jabia/Git/aily-ai-fin"
    data = analyze_repository(repo_path)
    plot_data(data)
    print_most_complex_and_modified(data)
