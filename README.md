# SlideBeautifier

## Overview

SlideBeautifier is an AI-powered Android application that automatically beautifies PowerPoint presentations by combining the content from one presentation with the design style of another. The application uses an Android frontend, a FastAPI backend, and the OpenAI API to generate a new presentation while preserving the desired visual style.

---

# Group Members

- Member 1: Guanyu Cheng
- Member 2: Lihang Jin

---

# Features

- Upload a reference PowerPoint (design template)
- Upload a content PowerPoint
- AI-generated slide planning using OpenAI
- Generate a new PowerPoint presentation
- Preview generated slides
- Download the generated PPTX file

---

# Project Architecture

```
Android App (Jetpack Compose)
            │
            │ HTTP (Retrofit)
            ▼
       FastAPI Backend
            │
            ├── PPT Reader
            ├── OpenAI API
            ├── PPT Writer
            └── PPT Preview Generator
            │
            ▼
      Generated PPTX File
```

---

# Technologies

## Frontend

- Android Studio
- Kotlin
- Jetpack Compose
- Retrofit
- Coil

## Backend

- Python 3.11+
- FastAPI
- Uvicorn
- python-pptx
- python-dotenv

## AI Service

- OpenAI Responses API
- GPT-5.4-mini

---

# Project Structure

```
SlideBeautifier/

app/
backend/

README.md
```

Backend directory:

```
backend/
│
├── main.py
├── requirements.txt
├── services/
├── ppt_reader/
├── ppt_writer/
├── uploads/
└── results/
```

---

# Prerequisites

Please install the following software before running the project.

- Android Studio
- Python 3.11 or newer
- Microsoft PowerPoint (required for preview image generation)
- Android SDK Platform Tools (adb)

---

# Backend Setup

Open a terminal.

```
cd backend
```

Create a virtual environment.

```
python -m venv .venv
```

Activate the virtual environment.

Windows:

```
.venv\Scripts\activate
```

Install all required packages.

```
pip install -r requirements.txt
```

---

# OpenAI API Configuration

Create a file named

```
backend/.env
```

Add your API key.

```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
```

You must obtain an API key from the OpenAI Platform and enable API billing.

---

# Running the Backend

Activate the virtual environment.

```
cd backend

.venv\Scripts\activate
```

Start FastAPI.

```
uvicorn main:app --host 0.0.0.0 --port 8080
```

When the backend starts successfully, you should see:

```
Uvicorn running on http://0.0.0.0:8080
```

---

# Configure Android Emulator

Open another terminal and execute:

```
adb reverse tcp:8080 tcp:8080
```

If adb is not in your PATH:

```
C:\Users\<username>\AppData\Local\Android\Sdk\platform-tools\adb.exe reverse tcp:8080 tcp:8080
```

---

# Running the Android Application

1. Open the project in Android Studio.
2. Wait for Gradle Sync to complete.
3. Launch an Android Emulator.
4. Run the application.

---

# Application Workflow

1. Launch the application.
2. Press **Start**.
3. Upload the reference PowerPoint.
4. Upload the content PowerPoint.
5. Press **Beautify Slides**.
6. Wait for AI processing.
7. Preview the generated presentation.
8. Download the generated PPTX file.

---

# Tested Environment

- Windows 11
- Android Studio Panda
- Python 3.11
- Android Emulator API 37
- FastAPI
- OpenAI Python SDK

---

# Known Limitations

- Internet connection is required.
- OpenAI API billing must be enabled.
- Preview image generation requires Microsoft PowerPoint on Windows.
- Generation speed depends on the OpenAI API response time.

---

# External Libraries

## Android

- Jetpack Compose
- Retrofit
- Coil

## Backend

- FastAPI
- Uvicorn
- python-pptx
- python-dotenv
- OpenAI Python SDK

---

# AI Usage

ChatGPT was used as a development assistant during implementation. All generated code was reviewed, modified, tested, and integrated by the project team before submission.

---

# Notes

- Do **NOT** commit your `.env` file to Git.
- Do **NOT** upload your OpenAI API key to GitHub.
- Ensure FastAPI is running before launching the Android application.

---

# License

This project was developed for educational purposes only.