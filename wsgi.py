from app import app, processor

# Ensure background RTSP thread processor is active when spawned by Gunicorn
if not processor.running:
    processor.start()

if __name__ == "__main__":
    app.run()
