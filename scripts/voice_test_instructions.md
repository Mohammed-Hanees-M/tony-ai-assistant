# Tony Live Voice Integration Test

This script enables end-to-end real-time testing of Tony's voice pipeline, combining Speech-to-Text (STT), the Unified Cognitive Brain, and Text-to-Speech (TTS).

## Prerequisites

You must have a microphone and speakers connected. 

### Required Dependencies
Install the necessary audio and speech libraries:
```bash
pip install speechrecognition pyttsx3 pyaudio
```

*Note: On Windows, `pyaudio` may require additional build tools or a pre-compiled wheel if the pip install fails.*

## How to Run

1. Ensure Tony's backend dependencies are installed.
2. Ensure Ollama is running locally (for the brain).
3. Execute the test harness:
   ```bash
   python scripts/live_voice_test.py
   ```

## Interaction Instructions

1. **Speak**: When prompted with `[LISTENER] Thinking...`, speak your request.
2. **Listen**: Tony will process the request through his cognitive modules (Memory, Graph, Planner) and begin streaming a response.
3. **Interrupt**: Press the **[Enter]** key at any time while Tony is speaking. Tony will immediately halt his speech and clear his internal streaming buffer.
4. **Exit**: Say "Exit" or press `Ctrl+C`.

## Features Tested
- **STT Accuracy**: Verification of human speech transcription.
- **Cognitive Latency**: Wall-clock measurement of brain processing time before speech begins.
- **Streaming TTS**: Incremental synthesis of tokens into spoken words.
- **Duplex Interruption**: Hotkey-triggered halt of the text-to-speech engine.
- **Voice States**: Visual logging of `LISTENING` -> `THINKING` -> `SPEAKING` transitions.
