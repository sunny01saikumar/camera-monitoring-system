import os
import sys
import urllib.request
import config

def download_progress(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = min(100, read_so_far * 100 / total_size)
        sys.stdout.write(f"\rDownloading: {percent:.2f}% ({read_so_far / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB)")
        sys.stdout.flush()
    else:
        sys.stdout.write(f"\rDownloading: {read_so_far / (1024*1024):.2f} MB")
        sys.stdout.flush()

def main():
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    if os.path.exists(config.MODEL_PATH):
        print(f"Model already exists at {config.MODEL_PATH}. Skipping download.")
        return

    print(f"Downloading YOLOv8n ONNX model from {config.MODEL_URL}...")
    try:
        # Install a custom opener to set the User-Agent header (required by Hugging Face)
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')]
        urllib.request.install_opener(opener)

        urllib.request.urlretrieve(config.MODEL_URL, config.MODEL_PATH, download_progress)
        print("\nDownload complete successfully!")
    except Exception as e:
        print(f"\nError downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
