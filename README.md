# Suraksha-Drishti: 100% Local KYC DNA Forensics

Suraksha-Drishti is a privacy-first, 100% local KYC verification and document forensics pipeline. It uses Google's Gemma 3 vision model (running locally via Ollama) to read documents (Aadhaar, PAN, ITR, Salary Slips) without internet access, and then passes the extracted data through a mathematical and visual DNA Forensics Engine.

All image processing, metadata analysis, font consistency checks, and QR code decoding happen entirely on your device. Your sensitive documents never leave your machine.

---

## 🚀 Quick Start Guide

To run this project from scratch on your own machine, follow these steps exactly:

### 1. Install Ollama & Gemma 3 (Local AI)
You need to install Ollama to run the AI text extraction locally.
1. Download and install **[Ollama](https://ollama.com/download)**.
2. Once installed, open a new Terminal/Command Prompt and run:
   ```bash
   ollama run gemma3:4b
   ```
3. This will download the 3.3 GB vision model. Once the download finishes, you can close the terminal. Ensure the Ollama app is running in your background (you should see the llama icon in your system tray).

### 2. Setup the Python Backend (FastAPI)
The backend requires Python 3.10+ and uses a virtual environment.
1. Open a terminal in the root of the cloned project.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   
   # On Windows:
   .\.venv\Scripts\activate
   # On Mac/Linux:
   source .venv/bin/activate
   ```
3. Create your environment variables file:
   Rename the provided `.env.example` file to `.env` and paste your Gemini API key inside it.
   ```bash
   cp .env.example .env
   ```
   *(You can get a free API key from [Google AI Studio](https://aistudio.google.com/))*

4. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```
   *The backend will now be running at `http://127.0.0.1:8000`*

### 3. Setup the Frontend (Vite + React)
The frontend requires Node.js installed.
1. Open a **new** terminal in the root of the cloned project.
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install the Node modules:
   ```bash
   npm install
   ```
4. Start the frontend development server:
   ```bash
   npm run dev
   ```
   *The web UI will be accessible at the localhost URL provided in the terminal (usually `http://localhost:5173`).*

---

## 🛠 Features Included
- **Aadhaar Forensics**: Verhoeff algorithm checks, mathematical secure QR decryption, ELA tampering checks.
- **PAN Forensics**: Structural regex verification, name match verification against Aadhaar.
- **Universal PDF Support**: Directly converts PDFs to images locally (`pypdfium2`) to feed into the Gemma 3 model.
- **0 Data Leaks**: Built with offline AI to guarantee compliance and data security.
