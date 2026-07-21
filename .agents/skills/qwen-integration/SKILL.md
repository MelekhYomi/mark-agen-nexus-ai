---
name: qwen-integration
description: Guides development and API interaction using Alibaba Cloud's Qwen AI models and Qwen cloud storage resources while strictly avoiding Vertex AI, Google Cloud Studio, or Gemini.
---

# Qwen AI & Cloud Resources Integration Skill

This skill governs all code development, service integration, and agent actions involving LLMs, AI agents, and associated cloud resources for the Nexus AI application. It mandates the use of Alibaba Cloud's Qwen models and Qwen-compatible resources while completely blocking any Google Cloud Vertex AI, Google Cloud Studio, or Gemini components.

---

## 🚫 Strictly Forbidden Services

Under no circumstances should the following Google Cloud or Gemini services/libraries be introduced, configured, or queried:
- **Vertex AI SDK** (`google-cloud-aiplatform`)
- **Google Generative AI SDK** (`google-generativeai`)
- **Google AI Studio**
- **Google Cloud Storage (GCS)** (for AI-related objects, data sets, or outputs)
- **Gemini models** (e.g., `gemini-1.5-pro`, `gemini-1.5-flash`)

---

## 🎯 Mandated Architecture & Technologies

### 1. Qwen Model Configuration
Always utilize settings from `backend/app/config.py` for LLM queries:
- **Model**: `qwen-max` (or other approved Qwen series models).
- **API Base**: `https://dashscope.aliyuncs.com/compatible-mode/v1` or the specific workspace compatible mode base url found in the environment.
- **Authentication**: `Bearer <QWEN_API_KEY>` loaded from the environment/config.

### 2. Standard Client Usage
Always prefer using the existing `QwenClient` class located at `[qwen_client.py](file:///c:/Users/iYomi/Desktop/Mark%20Agen%20-%20Nexus%20AI/backend/app/agents/qwen_client.py)` for any backend agent interactions.
Example usage:
```python
from app.agents.qwen_client import qwen_client

# Messages format: List of dicts with 'role' and 'content'
messages = [
    {"role": "system", "content": "You are a professional SEO expert..."},
    {"role": "user", "content": "Analyze my page and give recommendations..."}
]

response = await qwen_client.chat_completion(messages=messages, temperature=0.3)
```

### 3. Handling Qwen Thinking/Reasoning Output
Qwen models (such as `qwen-max` and `qwen-plus`) support returning a separate `reasoning_content` field in the chat completion message object. When parsing or rendering agent processes, always attempt to read and display this reasoning content:
```python
message = response["choices"][0]["message"]
content = message.get("content")
reasoning = message.get("reasoning_content") # Capture the deep thinking process!
```

### 4. Qwen-Compatible Cloud Storage
All file storage, media uploads, or AI training/fine-tuning datasets must be configured to use Qwen-compatible cloud storage:
- **Standard S3 / OSS Compatibility**: Use Alibaba Cloud Object Storage Service (OSS) or S3-compatible APIs.
- Do NOT configure or write code targetting Google Cloud Storage buckets (`gs://...` or `google-cloud-storage` library).

---

## 🔑 Missing Configuration & API Keys Procedure

If any key configurations (specifically `QWEN_API_KEY` or `QWEN_API_BASE`) are missing or contain default placeholders in `.env`, execute the following procedure:
1. **Interrupt & Verify**: Immediately halt any operations that require AI capabilities.
2. **Request API Credentials**: Politely prompt the user to provide their valid Qwen API key or custom DashScope Maas workspace endpoint.
3. **Save Safely**: Assist the user in writing these variables directly into `backend/.env` without exposing them in git or public code repositories.
