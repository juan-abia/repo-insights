import matplotlib.pyplot as plt
import subprocess
import os


def get_file_lines(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        return len(file.readlines())


def get_times_modified(file_path):
    result = subprocess.run(
        ['git', 'log', '--pretty=format:', '--name-only', f'--since="1 year ago"', file_path],
        text=True,
        capture_output=True
    )
    return len([line for line in result.stdout.split('\n') if line])


def analyze_repository(repo_path):
    os.chdir(repo_path)
    data = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(root, file)
            if not file_path.endswith(('.py', '.java', '.js', '.cpp', '.h', '.c')):  # add other file extensions if needed
                continue
            complexity = get_file_lines(file_path)
            mod_freq = get_times_modified(file_path)
            data.append((file_path, complexity, mod_freq))
    return data


def plot_data(data):
    x = [item[1] for item in data]  # complexity
    y = [item[2] for item in data]  # mod_freq
    plt.scatter(x, y)
    plt.title('Complexity vs Times Modified')
    plt.xlabel('Complexity (Lines of Code)')
    plt.ylabel('Modification Frequency (Past Year)')
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    repo_path = "/Users/jabia/Git/aily-ai-fin"
    data = analyze_repository(repo_path)
    plot_data(data)
