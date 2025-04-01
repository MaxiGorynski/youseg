import os
import argparse
import yt_dlp
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)


def download_audio_segment(video_url, start_time, end_time, output_file="output.mp3"):
    """
    Download audio segment from a YouTube video.

    Args:
        video_url (str): YouTube video URL
        start_time (str): Start time in format HH:MM:SS
        end_time (str): End time in format HH:MM:SS
        output_file (str): Output file name

    Returns:
        str: Path to the downloaded file
    """
    # Create a temporary folder for downloads
    os.makedirs("temp", exist_ok=True)

    # First, download the entire audio
    temp_file = os.path.join("temp", "full_audio.mp3")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': temp_file.replace(".mp3", ""),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    # Then, extract the segment using ffmpeg
    cmd = [
        'ffmpeg',
        '-i', temp_file,
        '-ss', start_time,
        '-to', end_time,
        '-c:a', 'copy',
        output_file
    ]

    subprocess.run(cmd, check=True)

    # Clean up
    os.remove(temp_file)

    return output_file


# Command line interface
def cli():
    parser = argparse.ArgumentParser(description='Download audio segment from YouTube video')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('start_time', help='Start time (HH:MM:SS)')
    parser.add_argument('end_time', help='End time (HH:MM:SS)')
    parser.add_argument('-o', '--output', default='output.mp3', help='Output file name')

    args = parser.parse_args()

    output_file = download_audio_segment(args.url, args.start_time, args.end_time, args.output)
    print(f"Audio segment downloaded to {output_file}")


# Web API
@app.route('/', methods=['GET'])
def index():
    """Serve the HTML form interface"""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Audio Downloader</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="text"], input[type="url"] {
                width: 100%;
                padding: 8px;
                box-sizing: border-box;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            button {
                background-color: #4285f4;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #3367d6;
            }
            .status {
                margin-top: 20px;
                padding: 10px;
                border-radius: 4px;
                display: none;
            }
            .loading {
                display: none;
                margin-top: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <h1>YouTube Audio Segment Downloader</h1>
        <form id="downloadForm" action="/download" method="post">
            <div class="form-group">
                <label for="url">YouTube URL:</label>
                <input type="url" id="url" name="url" required placeholder="https://www.youtube.com/watch?v=...">
            </div>
            <div class="form-group">
                <label for="start">Start Time (HH:MM:SS):</label>
                <input type="text" id="start" name="start" required placeholder="00:30:00 or 01:45">
            </div>
            <div class="form-group">
                <label for="end">End Time (HH:MM:SS):</label>
                <input type="text" id="end" name="end" required placeholder="01:45:00 or 02:30">
            </div>
            <button type="submit">Download Audio Segment</button>
        </form>
        <div id="loading" class="loading">
            <p>Downloading and processing... This may take a minute.</p>
        </div>
        <div id="status" class="status"></div>

        <script>
            document.getElementById('downloadForm').addEventListener('submit', function(e) {
                e.preventDefault();

                const loading = document.getElementById('loading');
                loading.style.display = 'block';

                const formData = new FormData(this);
                const url = formData.get('url');
                const start = formData.get('start');
                const end = formData.get('end');

                // Redirect to the download endpoint
                window.location.href = `/download?url=${encodeURIComponent(url)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;

                // Reset form and hide loading after a delay
                setTimeout(() => {
                    loading.style.display = 'none';
                }, 5000);
            });
        </script>
    </body>
    </html>
    """
    return html


@app.route('/download', methods=['GET'])
def download_endpoint():
    video_url = request.args.get('url')
    start_time = request.args.get('start')
    end_time = request.args.get('end')

    if not all([video_url, start_time, end_time]):
        return jsonify({"error": "Missing parameters. Required: url, start, end"}), 400

    try:
        output_file = download_audio_segment(video_url, start_time, end_time)
        return send_file(output_file, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # If arguments are provided, run CLI
        cli()
    else:
        # Otherwise, start web server
        print("Starting web server. Access the web interface at http://localhost:5001/")
        app.run(debug=True, host='0.0.0.0', port=5001)