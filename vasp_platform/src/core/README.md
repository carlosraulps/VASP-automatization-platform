# Core Infrastructure (`src/core/`)

This directory contains the foundational logic that powers the entire platform. It acts as the "Brain Stem" of the agentic system.

## Philosophy
**"Build Once, Import Everywhere."**
Core components are agent-agnostic. Whether it's the Translator, Manager, or Physicist, they all rely on these shared utilities.

## Components

### 1. LLM Adapter (`llm.py`)
-   **Role**: A robust wrapper around the Google GenAI SDK.
-   **Features**:
    -   **Centralized Auth**: Handles API keys from `.env` automatically.
    -   **Error Handling**: Catches network errors and API quota limits, preventing agent crashes.
    -   **Abstraction**: Allows swapping the underlying model (e.g., `gemini-3-flash-preview`) in one place.

### 2. State Management (`state.py`)
-   **Role**: Tracks the short-term memory of an active session.
-   **Features**:
    -   **Context**: Stores the currently selected material and conversation history.
    -   **Job Queue**: Temporarily holds `VaspJob` objects before they are committed to a Manifest.

## Best Practices
-   **Stateless Agents**: Agents should rely on `manifests` for long-term state and `core.state` only for the immediate session.
-   **No Direct API Calls**: All LLM interaction MUST go through `GoogleGenAIAdapter`.
