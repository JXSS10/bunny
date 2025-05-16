import os
from flask import Flask, render_template, request, jsonify
import json
import shutil # For cache clearing
import math   # For file size formatting

app = Flask(__name__)

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads') # سيتم إنشاء مجلد 'downloads' بجانب app.py
SUBJECT_FOLDERS_CONFIG = {
    "PHY": "Physics",
    "CHEM": "Chemistry",
    "MATHS": "Maths",
    "BIO": "Biology"
}

# Ensure download and subject folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
for subject_code in SUBJECT_FOLDERS_CONFIG.keys():
    subject_path = os.path.join(UPLOAD_FOLDER, subject_code)
    if not os.path.exists(subject_path):
        os.makedirs(subject_path)
# --- End Configuration ---


# --- Helper Functions ---
def get_folder_size(folder_path):
    total_size = 0
    for dirpath, _, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
# --- End Helper Functions ---

# ---- الصفحة الرئيسية مع الـ GIF ----
@app.route('/')
def home():
    return """
<center>
    <img src="https://i.giphy.com/media/3o7abAHdYvZdBNnGZq/giphy.webp" style="border-radius: 12px;"/>
</center>
<style>
    body {
        background: antiquewhite;
    }
</style>"""
# ---- نهاية الصفحة الرئيسية ----


# ---- صفحة أداة التحميل ----
@app.route('/downloader')
def downloader_page():
    # هذا المسار سيعرض واجهة المستخدم الخاصة بأداة التحميل
    return render_template('index.html')
# ---- نهاية صفحة أداة التحميل ----


@app.route('/analyze', methods=['POST'])
def analyze_video_url():
    video_url = request.form.get('url')
    if not video_url:
        return jsonify({'error': 'No URL provided'}), 400

    print(f"Analyzing URL (from Flask): {video_url}")

    ### PYTHON BACKEND LOGIC NEEDED HERE ###
    # For now, we'll return MOCK data.
    mock_data = {
        "urls": {
            "240p": {"url": f"{video_url.split('?')[0]}/240p.m3u8", "resolution": "240p"},
            "360p": {"url": f"{video_url.split('?')[0]}/360p.m3u8", "resolution": "360p"},
            "720p": {"url": f"{video_url.split('?')[0]}/720p.m3u8", "resolution": "720p"}
        },
        "guid": "mock_guid_from_flask_123",
        "context_id": "mock_context_id_abc",
        "secret": "mock_secret_xyz",
        "server_id": "mock_server_id_001",
    }
    return jsonify(mock_data)
    ### END OF PYTHON BACKEND LOGIC NEEDED HERE ###

@app.route('/download', methods=['POST'])
def download_video_stream():
    data = request.json
    stream_url = data.get('url')
    quality_resolution = data.get('quality')
    file_name_from_js = data.get('file_name', 'downloaded_video.mp4')
    subject_code = data.get('subject')

    print(f"Download request (Flask):")
    print(f"  Stream URL: {stream_url}")
    print(f"  Quality: {quality_resolution}")
    print(f"  Output Filename: {file_name_from_js}")
    print(f"  Subject: {subject_code}")

    ### PYTHON BACKEND LOGIC NEEDED HERE ###
    # Simulate download
    save_dir = UPLOAD_FOLDER
    if subject_code and subject_code in SUBJECT_FOLDERS_CONFIG:
        save_dir = os.path.join(UPLOAD_FOLDER, subject_code)

    output_filepath = os.path.join(save_dir, file_name_from_js)

    try:
        with open(output_filepath, 'w') as f:
            f.write(f"Mock content for {file_name_from_js} from URL: {stream_url}")
        print(f"Simulated download: {output_filepath} created.")
        return jsonify({'status': 'success', 'message': f'Simulated download successful for {file_name_from_js}'})
    except Exception as e:
        print(f"Error during simulated download: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    ### END OF PYTHON BACKEND LOGIC NEEDED HERE ###

@app.route('/subjects', methods=['GET'])
def get_subject_info():
    subject_data = {}
    for code, name in SUBJECT_FOLDERS_CONFIG.items():
        folder_path = os.path.join(UPLOAD_FOLDER, code)
        count = 0
        size_bytes = 0
        if os.path.exists(folder_path):
            count = len([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
            size_bytes = get_folder_size(folder_path)
        
        subject_data[code] = {
            "name": name,
            "count": count,
            "size": format_size(size_bytes)
        }
    return jsonify(subject_data)

@app.route('/clear-cache', methods=['POST'])
def clear_server_cache():
    try:
        for item_name in os.listdir(UPLOAD_FOLDER):
            item_path = os.path.join(UPLOAD_FOLDER, item_name)
            if os.path.isdir(item_path):
                if item_name in SUBJECT_FOLDERS_CONFIG.keys():
                    for sub_item_name in os.listdir(item_path):
                        sub_item_path = os.path.join(item_path, sub_item_name)
                        if os.path.isfile(sub_item_path) or os.path.islink(sub_item_path):
                            os.unlink(sub_item_path)
                        elif os.path.isdir(sub_item_path):
                            shutil.rmtree(sub_item_path)
            elif os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)

        print("Cache cleared (all files in download folders deleted).")
        return jsonify({'success': True, 'message': 'Cache cleared successfully on server.'})
    except Exception as e:
        print(f"Error clearing cache: {e}")
        return jsonify({'success': False, 'message': f'Failed to clear cache: {str(e)}'}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) # يأخذ البورت من متغير البيئة أو يستخدم 5000 كافتراضي
    app.run(host='0.0.0.0', port=port, debug=True) # debug=True مفيد أثناء التطوير
