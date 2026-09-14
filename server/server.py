from flask import Flask, jsonify, request
import os
import subprocess
from datetime import datetime

app = Flask(__name__)

# Global state
run_in_progress = False
current_run_log_path = None

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOARDS_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'olp_xdv_agent', 'olp_xdv', 'output', 'boards'))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

def get_board_files():
    files = []
    for file in os.listdir(BOARDS_DIR):
        if file.startswith('board_') and file.endswith('.txt'):
            date_str = file[6:-4]  # Remove 'board_' and '.txt'
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                files.append((date, file))
            except ValueError:
                continue
    # Sort by date descending
    files.sort(key=lambda x: x[0], reverse=True)
    return files[:14]  # Last 14 dates

@app.route('/boards', methods=['GET'])
def get_boards():
    board_files = get_board_files()
    dates = [file[0].strftime('%Y-%m-%d') for date, file in board_files]
    return jsonify({'boards': dates})

@app.route('/boards/<date>', methods=['GET'])
def get_board(date):
    date_str = date
    board_file = os.path.join(BOARDS_DIR, f'board_{date_str}.txt')
    if not os.path.exists(board_file):
        return jsonify({'error': 'Board not found'}), 404
    with open(board_file, 'r') as f:
        content = f.read()
    return jsonify({'content': content})

@app.route('/run', methods=['POST'])
def run():
    global run_in_progress, current_run_log_path
    if run_in_progress:
        return jsonify({'error': 'Run already in progress'}), 409
    run_in_progress = True
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(LOGS_DIR, f'run_{timestamp}.log')
    try:
        # Run the script and capture output
        with open(log_path, 'w') as log_file:
            process = subprocess.run(['python', os.path.join(BASE_DIR, '..', '..', 'run_daily.py')],
                                     stdout=log_file, stderr=subprocess.STDOUT)
        current_run_log_path = log_path
    finally:
        run_in_progress = False
    return jsonify({'status': 'run_started', 'log_file': log_path})

@app.route('/run/status', methods=['GET'])
def run_status():
    if run_in_progress:
        return jsonify({'in_progress': True, 'log': 'Run is currently in progress'}), 200
    if current_run_log_path and os.path.exists(current_run_log_path):
        with open(current_run_log_path, 'r') as f:
            log_content = f.read()
        # Return the last 20 lines as a preview
        lines = log_content.splitlines()
        tail = lines[-20:] if len(lines) > 20 else lines
        return jsonify({'in_progress': False, 'log': '\n'.join(tail), 'log_file': current_run_log_path})
    else:
        return jsonify({'in_progress': False, 'log': 'No runs recorded'}), 200

if __name__ == '__main__':
    # Bind to LAN IP, not 0.0.0.0
    import socket
    hostname = socket.gethostname()
    # Get the LAN IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        lan_ip = s.getsockname()[0]
    except Exception:
        lan_ip = '127.0.0.1'
    s.close()
    app.run(host=lan_ip, port=5000, debug=False)