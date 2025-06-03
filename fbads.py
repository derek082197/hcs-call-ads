import os
import sys
import subprocess
import requests
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

# =========================================
# HCS AD GENERATOR (Local Desktop Version)
# =========================================
# Features:
#  1) Generate TTS via ElevenLabs (hard-coded key below)
#  2) Create lip-synced video from a static image using Wav2Lip
#  3) Append customizable benefit slides
#  4) Offer pre-set templates (ACA, Final Expense) or custom scripts
#  5) Save output MP4s locally under “output/”
#
# To run:
#  1. Install dependencies (moviepy, requests, Wav2Lip requirements)
#  2. Place “wav2lip_gan.pth” in Wav2Lip/checkpoints/
#  3. Place “spokesperson.jpg” (or your avatar) in this folder
#  4. Run: python lip_sync_ad_generator.py
#
# Note: Change fonts, durations, or templates as needed.

# ------ Configuration (Hard-coded Key) ------
ELEVENLABS_API_KEY = "sk_55bb280a58baa1308015d462f622c89e7c596727589c750f"

VOICE_ID = "9BWtsMINqrJLrRacOk9x"           # “Rachel” female voice on ElevenLabs
SPOKESPERSON_IMAGE = "spokesperson.jpg"      # Static image for lip-sync
WAV2LIP_PATH = "Wav2Lip"                     # Path to the cloned Wav2Lip repo
OUTPUT_DIR = "output"                        # Where to save generated files
VIDEO_SIZE = (720, 1280)                     # 9:16 vertical for Facebook call ads

# Ensure output folder exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ------ Utility Functions ------

def generate_audio(text, output_path):
    """
    Generate TTS audio via ElevenLabs and save to output_path.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.7,
            "similarity_boost": 0.75
        }
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"✔️ Audio saved to {output_path}")
    else:
        raise RuntimeError(f"ElevenLabs TTS failed: {resp.status_code} {resp.text}")
    return output_path

def generate_lip_synced_video(audio_path, image_path, output_path):
    """
    Use Wav2Lip to produce a lip-synced video from a static image + generated audio.
    Requires wav2lip_gan.pth in Wav2Lip/checkpoints/.
    """
    checkpoint = os.path.join(WAV2LIP_PATH, "checkpoints", "wav2lip_gan.pth")
    if not os.path.exists(checkpoint):
        raise FileNotFoundError("Place wav2lip_gan.pth into Wav2Lip/checkpoints/ first.")
    cmd = [
        "python",
        os.path.join(WAV2LIP_PATH, "inference.py"),
        "--checkpoint_path", checkpoint,
        "--face", image_path,
        "--audio", audio_path,
        "--outfile", output_path
    ]
    print("🔄 Running Wav2Lip inference…")
    subprocess.run(cmd, check=True)
    print(f"✔️ Lip-synced video saved to {output_path}")
    return output_path

def create_benefit_slides(video_clip, benefit_texts, phone_number, output_path):
    """
    Append benefit slides after the lip-synced clip.
    Each slide shows one benefit for 3 seconds, then a final CTA slide.
    """
    slide_clips = []
    for text in benefit_texts:
        txt_clip = (
            TextClip(text, fontsize=48, font="Arial-Bold", color="white",
                     size=video_clip.size, method="caption", align="center")
            .set_duration(3)
            .set_position("center")
        )
        slide_clips.append(txt_clip)

    # Final CTA slide
    cta_text = f"Call Now: {phone_number}"
    cta_clip = (
        TextClip(cta_text, fontsize=60, font="Arial-Bold", color="yellow",
                 size=video_clip.size, method="caption", align="center")
        .set_duration(4)
        .set_position("center")
    )
    slide_clips.append(cta_clip)

    slides_concat = concatenate_videoclips(slide_clips, method="compose")
    # Merge original lip-synced audio with the slides
    final = concatenate_videoclips([video_clip, slides_concat.set_audio(video_clip.audio)], method="compose")
    final.write_videofile(output_path, fps=24)
    print(f"✔️ Final ad saved to {output_path}")
    return output_path

# ------ Pre-set Templates & Benefits ------

ACA_TEMPLATE = (
    "Hello! I'm excited to share that you may qualify for a health insurance plan with $0 monthly premiums, "
    "thanks to new government subsidies under the Affordable Care Act. These plans can include dental, vision, "
    "and prescription coverage — all at no cost if you qualify. The enrollment is fast and easy — it takes just 5 minutes. "
    "Call us now at (561) 576-0801 to check your eligibility and get covered today!"
)
FE_TEMPLATE = (
    "Hi there! Looking for affordable final expense coverage? We offer guaranteed-issue plans with no medical exams, "
    "and competitive rates starting at just $20 a month. Your loved ones get peace of mind, and you get burial, funeral, "
    "and final expenses covered. Call (561) 576-0801 now to enroll in minutes, and secure your family’s future today!"
)

ACA_BENEFITS = [
    "$0 Health Plans – ACA Subsidies",
    "Dental, Vision & Prescriptions Included",
    "Fast 5-Minute Enrollment"
]
FE_BENEFITS = [
    "Guaranteed Issue – No Exam Required",
    "Rates Start at $20/Month",
    "Covers Burial & Funeral Costs"
]

# ------ Command-Line Menu ------

def show_menu():
    print("\n================ HCS Ad Generator =================")
    print("1) Generate ACA Ad")
    print("2) Generate Final Expense Ad")
    print("3) Custom Ad Script")
    print("4) Exit")
    choice = input("Choose an option [1-4]: ").strip()
    return choice

def generate_ad(template_text, benefit_list, output_prefix):
    # 1) Generate TTS audio
    audio_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_audio.wav")
    generate_audio(template_text, audio_path)

    # 2) Lip-sync video
    lip_video_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_lip.mp4")
    generate_lip_synced_video(audio_path, SPOKESPERSON_IMAGE, lip_video_path)

    # 3) Append benefit slides & save final ad
    lip_clip = VideoFileClip(lip_video_path)
    final_output = os.path.join(OUTPUT_DIR, f"{output_prefix}_final.mp4")
    create_benefit_slides(lip_clip, benefit_list, "(561) 576-0801", final_output)
    print(f"✅ Ad creation complete: {final_output}\n")

def main():
    while True:
        choice = show_menu()
        if choice == '1':
            print("Generating ACA Ad…")
            generate_ad(ACA_TEMPLATE, ACA_BENEFITS, "aca_ad")
        elif choice == '2':
            print("Generating Final Expense Ad…")
            generate_ad(FE_TEMPLATE, FE_BENEFITS, "fe_ad")
        elif choice == '3':
            custom_text = input("Enter your custom ad script: ").strip()
            print("Enter benefit bullet points (comma-separated):")
            bullets = input().split(',')
            benefit_list = [b.strip() for b in bullets if b.strip()]
            if not benefit_list:
                benefit_list = ["Affordable Coverage Available", "Call Now: (561) 576-0801"]
            generate_ad(custom_text, benefit_list, "custom_ad")
        elif choice == '4':
            print("Exiting… Thank you!")
            break
        else:
            print("Invalid selection. Please choose 1-4.")

if __name__ == "__main__":
    main()
