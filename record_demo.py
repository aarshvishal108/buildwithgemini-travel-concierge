import os
import shutil
import subprocess
import time
from playwright.sync_api import sync_playwright

RAW_DIR = "raw_recording"
FINAL_VIDEO = "demo_recording.mp4"
ARTIFACT_DIR = "/config/.gemini/antigravity/brain/c74edf6f-c796-453e-bfd4-526481af21eb"

def record_browser_session():
    os.makedirs(RAW_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(
            record_video_dir=RAW_DIR,
            record_video_size={"width": 1280, "height": 720},
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        
        print("Navigating to Wanderlust Web Frontend...")
        page.goto("https://travel-concierge-frontend-113901312269.us-east1.run.app")
        page.wait_for_timeout(2500)
        
        # --- Action 1: What app does best (Destination Search & A2UI) ---
        print("Submitting Prompt 1: Destination Search...")
        page.fill("#input", "Suggest top places in Japan for nature and scenery")
        page.wait_for_timeout(800)
        page.click("#form button")
        
        # Wait for agent reply bubble
        page.wait_for_selector(".msg-wrapper.agent .bubble", timeout=30000)
        page.wait_for_timeout(6000)  # Pause to let user view result
        
        # --- Action 2: Richer prompt (Postcard Image Generation & Tool Call) ---
        print("Submitting Prompt 2: Image Generation Tool Call...")
        page.fill("#input", "Generate a scenic travel postcard of Kyoto Bamboo Grove")
        page.wait_for_timeout(800)
        page.click("#form button")
        
        # Wait for the second agent reply
        page.wait_for_selector(".msg-wrapper.agent:nth-of-type(3) .bubble", timeout=45000)
        page.wait_for_timeout(7000)  # Pause to let user view generated postcard
        
        print("Closing browser session...")
        video_path = page.video.path()
        context.close()
        browser.close()
        return video_path

def add_music_and_export(webm_path):
    print(f"Raw video recorded at: {webm_path}")
    print("Combining video with upbeat lo-fi background music...")
    
    # Run ffmpeg to mix video and audio
    cmd = [
        "ffmpeg", "-y",
        "-i", webm_path,
        "-i", "lofi_track.wav",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        FINAL_VIDEO
    ]
    subprocess.run(cmd, check=True)
    print(f"Final demo video created: {FINAL_VIDEO}")
    
    # Copy to Artifacts directory
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    artifact_path = os.path.join(ARTIFACT_DIR, "demo_recording.mp4")
    shutil.copy(FINAL_VIDEO, artifact_path)
    print(f"Copied to artifact directory: {artifact_path}")

if __name__ == '__main__':
    webm_file = record_browser_session()
    add_music_and_export(webm_file)
