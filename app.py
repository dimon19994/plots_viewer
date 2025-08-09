import os
import json

from flask import Flask, render_template, request, send_from_directory, abort
import plotly.io as pio



app = Flask(__name__)
PLOT_ROOT = os.path.join('static', 'plots')

@app.route('/')
def index():
    rel_path = request.args.get('path', '')  # относительный путь от корня
    abs_path = os.path.join(PLOT_ROOT, rel_path)

    if not os.path.isdir(abs_path):
        return abort(404)

    entries = []
    for name in os.listdir(abs_path):
        full_path = os.path.join(abs_path, name)
        rel_entry = os.path.join(rel_path, name).replace("\\", "/")

        try:
            stat = os.stat(full_path)
            timestamp = stat.st_ctime  # или st_mtime — см. ниже
        except FileNotFoundError:
            continue

        if os.path.isdir(full_path):
            entries.append({'type': 'folder', 'name': name, 'path': rel_entry, 'time': timestamp})
        elif name.endswith('.html') or name.endswith('.json'):
            entries.append({'type': 'file', 'name': name, 'path': rel_entry, 'time': timestamp})

    # Сортировка: сначала новые
    entries.sort(key=lambda x: x['time'], reverse=False)

    parent_path = os.path.dirname(rel_path.rstrip("/")) if rel_path else None

    return render_template("index.html", entries=entries, current=rel_path, parent=parent_path)

@app.route('/plot/<path:filename>')
def plot(filename):
    return send_from_directory(PLOT_ROOT, filename)

@app.route('/plot_view/<path:filename>')
def plot_view(filename):
    parent_folder = os.path.dirname(filename)
    abs_folder = os.path.join(PLOT_ROOT, parent_folder)
    current_file = os.path.basename(filename)

    try:
        # Собираем все .html файлы с датой изменения
        files_with_time = []
        for f in os.listdir(abs_folder):
            if f.endswith('.html') or f.endswith('.json'):
                full_path = os.path.join(abs_folder, f)
                try:
                    mtime = os.path.getmtime(full_path)
                    files_with_time.append((f, mtime))
                except FileNotFoundError:
                    continue

        # Сортируем по дате (сначала новые)
        sorted_files = [f for f, _ in sorted(files_with_time, key=lambda x: x[1], reverse=False)]
    except FileNotFoundError:
        sorted_files = []

    # Найдём текущий индекс
    try:
        index = sorted_files.index(current_file)
    except ValueError:
        index = -1

    prev_file = sorted_files[index - 1] if index > 0 else None
    next_file = sorted_files[index + 1] if index != -1 and index + 1 < len(sorted_files) else None

    dirs = "/".join(parent_folder.split('/')[:-2])

    all_files = []
    for root, dirs, files in os.walk("./static/plots/" + dirs):
        for file in files:
            if file == current_file:
                full_path = os.path.join(root, file)
                all_files.append(full_path)

    # Сортируем по времени изменения (от старых к новым)
    all_files.sort(key=os.path.getmtime)

    try:
        same_index = next(i for i in range(len(all_files)) if parent_folder in all_files[i])
    except ValueError:
        same_index = -1

    same_prev_file = all_files[same_index - 1] if same_index > 0 else None
    same_next_file = all_files[same_index + 1] if same_index != -1 and same_index + 1 < len(all_files) else None

    if filename.endswith(".json"):
        with open(f"./static/plots/{filename}", "r") as f:
            fig_json = json.load(f)

        fig = pio.from_json(json.dumps(fig_json))
        html_str = pio.to_html(fig, full_html=True, include_plotlyjs='cdn', config={"responsive": True})

        with open("./static/plots/plot_from_json.html", "w", encoding="utf-8") as f:
            f.write(html_str)
            filename = "plot_from_json.html"

    return render_template(
        'plot_view.html',
        filename=filename,
        parent=parent_folder,
        prev_path=os.path.join(parent_folder, prev_file) if prev_file else None,
        next_path=os.path.join(parent_folder, next_file) if next_file else None,
        same_prev_file=same_prev_file.replace("./static/plots/", "") if same_prev_file else None,
        same_next_path=same_next_file.replace("./static/plots/", "") if same_next_file else None,
    )


if __name__ == '__main__':
    app.run(debug=True)
