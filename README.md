# BetterTTS

Free, self-hosted AI text-to-speech for streamers. Powered by [Qwen3-TTS](https://huggingface.co/Qwen). No subscriptions, no cloud, no API keys — runs entirely on your PC.

Created by [@kindredspiritva](https://twitter.com/kindredspirityt)

---

## What is BetterTTS?

BetterTTS is a desktop app that turns chat messages into spoken audio using AI. It runs a local TTS server on your computer and connects to [Streamer.bot](https://streamer.bot/) so your viewers' messages get read aloud in high-quality AI voices.

Everything runs locally — no data ever leaves your machine.

## Features

### Preset Voices
Choose from 9 built-in voices across multiple styles:
- **Ryan** — Young American male, clear and natural
- **Vivian** — Young American female, warm and expressive
- **Aiden** — Young American male, confident
- **Serena** — Young American female, calm and articulate
- **Dylan** — Young American male, casual
- **Eric** — Middle-aged American male, deep and steady
- **Uncle_Fu** — Elderly Chinese male, wise and warm
- **Ono_Anna** — Young Japanese female, gentle
- **Sohee** — Young Korean female, bright and cheerful

### Voice Cloning
Upload a 5-15 second audio clip of any voice and clone it. Create reusable voice profiles that you can switch between at any time. Supports `.wav`, `.mp3`, `.flac`, and `.m4a` files.

### Voice Design
Describe a voice in plain text and the AI creates it — no reference audio needed. Example: *"A warm British female voice with a calm, soothing tone"*

### Style Instructions
Control how the voice speaks with natural language instructions:
- *"Speak cheerfully and energetically"*
- *"Use a calm, soothing tone"*
- *"Whisper dramatically"*
- *"Talk like a sports announcer"*

### 10 Languages
English, Chinese, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian

### Streamer.bot Integration
Built-in setup guide walks you through connecting BetterTTS to Streamer.bot step by step.

---

## Requirements

- **OS:** Windows 10 or 11
- **GPU:** NVIDIA GPU with 4+ GB VRAM recommended (GTX 600 series or newer). Works on CPU too, just slower. AMD/Intel GPUs run in CPU mode.
- **RAM:** 8 GB minimum, 16 GB recommended
- **Disk:** ~5-8 GB for model and dependencies
- **SoX:** Required for voice cloning. Download from [sox.sourceforge.net](https://sox.sourceforge.net)

---

## Getting Started

### 1. Install SoX (optional, for voice cloning)
Download and install SoX from [sox.sourceforge.net](https://sox.sourceforge.net). This is only needed if you want to use voice cloning.

### 2. Run Setup
Double-click `setup.bat`. It will:
- Check for a compatible Python version (3.10-3.12) and install Python 3.12 if needed
- Create a virtual environment
- Detect your GPU and install the appropriate PyTorch version
- Install all dependencies

This is a one-time step. Setup takes 5-10 minutes depending on your internet speed.

### 3. Launch BetterTTS
Double-click `start.bat` to open the app.

On first launch, you'll need to:
1. Go to the **Model** tab and select a model variant
2. Click **Load Model** — this downloads the AI model (~2.5-4.5 GB, one-time only)
3. Go to the **Server** tab and click **Start Server**

### 4. Connect to Streamer.bot
Click **Open Setup Guide** in the Server tab for step-by-step instructions. This will create "Set Global Variable for ttsText" and a C# code block to play the TTS. Add these to whatever actions you want the TTS to trigger, along with the respective text in the global variable.

You can also manually set up the integration using the C# code in `Streamerbot TTS Speak.txt`.

---

## Model Variants

| Model | Type | VRAM | Download | Best For |
|-------|------|------|----------|----------|
| CustomVoice 0.6B | Preset voices + style control | 4-6 GB | ~2.5 GB | Everyday streaming, lower-end GPUs |
| CustomVoice 1.7B | Preset voices + style control | 6-8 GB | ~4.5 GB | Higher quality voices |
| Base 0.6B | Voice cloning | 4-6 GB | ~2.5 GB | Cloning voices, lower-end GPUs |
| Base 1.7B | Voice cloning | 6-8 GB | ~4.5 GB | Higher fidelity cloned voices |
| VoiceDesign 1.7B | Create voices from text | 6-8 GB | ~4.5 GB | Designing custom voices without audio |

---

## API Endpoints

BetterTTS runs a local HTTP server (default port `7861`) with these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tts` | POST | Generate speech. Send `{"text": "..."}` and receive WAV audio |
| `/health` | GET | Server status and model info |
| `/settings` | GET | Current voice settings |
| `/profiles` | GET | List all voice profiles |
| `/profiles/active` | POST | Set the active voice profile |

---

## Troubleshooting

### Setup shows nothing / closes instantly
Make sure you're running `setup.bat` by double-clicking it, not from an elevated command prompt. If it still fails, right-click `setup.bat` and select "Run as administrator".

### CUDA not detected (NVIDIA GPU)
Update your NVIDIA drivers from [nvidia.com/download](https://www.nvidia.com/download/index.aspx). BetterTTS uses CUDA 11.8 which requires driver version 452.39 or newer. The app will still work on CPU if CUDA isn't available.

### "No matching distribution found for torch"
Your Python version is too new. BetterTTS requires Python 3.10, 3.11, or 3.12. Delete the `venv` folder and re-run `setup.bat` — it will install Python 3.12 automatically.

### SoX not found
Install SoX from [sox.sourceforge.net](https://sox.sourceforge.net). Alternatively, place a `sox` folder containing `sox.exe` inside the BetterTTS directory.

### Audio is silent
Check that your speakers/headphones are working. In Streamer.bot, make sure the BetterTTS action queue has **Blocking** enabled so messages play one at a time.

---

## Support

If you find BetterTTS useful, [consider donating to help out!](https://streamelements.com/kindredspiritva/tip)

---

## License

Open source. Free to use.
