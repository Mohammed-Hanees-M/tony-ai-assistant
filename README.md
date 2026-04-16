# Tony AI Assistant

Tony is a production-grade autonomous agentic AI assistant designed with a focus on conversational intelligence, context awareness, and tool-based execution.

## Core Features

- **Autonomous Agent Loop**: High-level planning and multi-step execution with self-critique and re-planning capabilities.
- **Advanced Memory Architecture**: Triple-tier memory system including Long-term, Episodic, and Reflective memory.
- **Voice Intelligence**: Integrated STT, TTS, and VAD (Voice Activity Detection) for real-time natural language interaction.
- **Decision Governance**: Human-in-the-loop approval system for high-risk tool operations.
- **Cognitive Controller**: Central hub orchestration for reasoning, planning, and knowledge retrieval.
- **Streaming Engine**: Low-latency sentence-aware audio and text streaming for a natural UX.

## Project Structure

- `apps/backend/`: Core FastAPI backend, logic, and agents.
- `scripts/`: Extensive verification and benchmarking suite.
- `docs/`: Technical and product documentation (Work in progress).
- `tests/`: Unit, integration, and E2E test suites.

## Getting Started

### Prerequisites
- Python 3.11+
- SQLite (for local database `tony.db`)

### Backend Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# Run the backend
uvicorn apps.backend.main:app --reload
```

## Running Verifications
To ensure Tony's cognitive pipelines are functioning correctly, run the verification scripts:
```bash
python scripts/verify_context_intelligence.py
python scripts/verify_memory_governance.py
```
