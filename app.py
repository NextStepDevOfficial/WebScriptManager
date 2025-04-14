from flask import Flask, render_template, redirect, url_for, Response
import os
import subprocess
import logging
import json

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Directory containing scripts
SCRIPTS_DIR = 'scripts'
AUTOSTART_FILE = 'autostart.json'

# Load or initialize autostart settings
if not os.path.exists(AUTOSTART_FILE):
    with open(AUTOSTART_FILE, 'w') as f:
        json.dump({}, f)

def load_autostart_settings():
    with open(AUTOSTART_FILE, 'r') as f:
        return json.load(f)

def save_autostart_settings(settings):
    with open(AUTOSTART_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def discover_scripts():
    scripts = {}
    for filename in os.listdir(SCRIPTS_DIR):
        if filename.endswith('.py'):
            script_name = filename[:-3]
            scripts[script_name] = {
                'path': os.path.join(SCRIPTS_DIR, filename),
                'status': 'stopped',
                'log_file': f'logs/{script_name}.log'
            }
    return scripts

script_status = discover_scripts()
autostart_settings = load_autostart_settings()

@app.route('/')
def index():
    # Update script statuses
    for script_name, script in script_status.items():
        script['status'] = 'running' if is_script_running(script_name) else 'stopped'
    return render_template('index.html', scripts=script_status, autostart=autostart_settings)

def start_script_logic(script_name):
    """Запускает скрипт без использования redirect или url_for."""
    if script_name in script_status:
        script_path = script_status[script_name]['path']
        log_file = script_status[script_name]['log_file']
        try:
            with open(log_file, 'w') as log:
                subprocess.Popen(['python3', script_path], stdout=log, stderr=log, text=True)
            script_status[script_name]['status'] = 'running'
            logging.info(f'Started script: {script_name}')
        except Exception as e:
            logging.error(f"Failed to start script {script_name}: {e}")

@app.route('/start/<script_name>')
def start_script(script_name):
    start_script_logic(script_name)
    return redirect(url_for('index'))

@app.route('/stop/<script_name>')
def stop_script(script_name):
    if script_name in script_status:
        os.system(f"pkill -f {script_status[script_name]['path']}")
        script_status[script_name]['status'] = 'stopped'
        logging.info(f'Stopped script: {script_name}')
    return redirect(url_for('index'))

@app.route('/autostart/<script_name>', methods=['POST'])
def toggle_autostart(script_name):
    autostart_settings[script_name] = not autostart_settings.get(script_name, False)
    save_autostart_settings(autostart_settings)
    logging.info(f'Toggled autostart for script: {script_name} to {autostart_settings[script_name]}')
    return redirect(url_for('index'))

@app.route('/logs/<script_name>')
def view_logs(script_name):
    if script_name in script_status:
        log_file = script_status[script_name]['log_file']
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()
            return render_template('logs.html', script_name=script_name, log_content=log_content)
        else:
            return render_template('logs.html', script_name=script_name, log_content="Log file not found.")
    return "Script not found", 404

def is_script_running(script_name):
    script_path = script_status[script_name]['path']
    result = subprocess.run(['pgrep', '-f', script_path], stdout=subprocess.PIPE)
    return result.returncode == 0

def start_autostart_scripts():
    """Запускает все скрипты, включённые в автозапуск."""
    for script_name, enabled in autostart_settings.items():
        if enabled and script_name in script_status:
            start_script_logic(script_name)

if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    start_autostart_scripts()
    app.run(debug=True)