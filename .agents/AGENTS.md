# Nexus AI - Project Customization Rules

This document outlines the strict behavioral and styling rules for all AI agents working on this project.

## Styling & Theme Rules

- **No Glassmorphism**: Do NOT use vibrant, colorful, or highly transparent glassmorphic background shades (such as purplish/bluish linear gradients like `rgba(28,28,43,0.6)` or `rgba(20,20,31,0.4)` combined with blur).
- **Default Initial Theme**: Always adhere to the neutral grey-black default initial theme defined by the original references.
  - Background variables:
    ```css
    --bg-0: #0a0a0f;
    --bg-1: #111118;
    --bg-2: #1a1a24;
    --bg-3: #24243a;
    ```
  - Card/container style: Use a clean, dark background with minimal transparency and subtle grey-white borders:
    ```css
    .glass { background: rgba(26, 26, 36, 0.6); backdrop-filter: blur(20px); border: 1px solid var(--border); }
    .glass-strong { background: rgba(26, 26, 36, 0.85); backdrop-filter: blur(24px); border: 1px solid var(--border-strong); }
    ```
- **Consistent Colors**: Use dark neutral shades. Avoid injecting ad-hoc colorful background panels, neon glows, or vibrant background colors unless explicitly requested. Keep the styling clean, formal, and premium.

- **Lock Landing Page**: Do NOT modify, replace, or alter the public landing page HTML (the `#landingPage` block) or its base desktop CSS/layout styles in `frontend/index.html` under any circumstances unless explicitly requested by the user. This landing page structure and styling has been fully approved and is completely locked.

## Accessibility, High Contrast & Theme-Aware Overrides Rules

- **Universal Readability Focus**: We must ensure that the application remains fully legible and beautiful across both manual and system light/dark theme transitions, catering specifically to users with low vision or other visual impairments.
- **Strict Color-Contrast Ratios**: Keep contrast compliant with WCAG AA/AAA standards:
  - For Light Theme: Secondary/dim texts should use dark high-contrast charcoal `--text-dim: #374151` (7.4:1 contrast ratio against white) and `--text-faint: #6b7280` (4.5:1 ratio) rather than light grays.
  - For Dark Theme: `--text-dim: #a1a1aa` and `--text-faint: #71717a` to maintain excellent legibility against dark backgrounds.
- **Parent-Aware Override Architecture**: To satisfy the **Lock Landing Page** requirement while making the application light-mode responsive, we do **NOT** rewrite hardcoded dark utility classes (like `text-white`, `text-gray-300`, `text-gray-400`) in the HTML. Instead, we declare specific parent-aware selector overrides inside the CSS style block:
  - Example: `.light-theme #landingPage .text-gray-300 { color: var(--text-dim) !important; }`
  - Normal text layouts with hardcoded `text-white` should be overridden to `var(--text)` when in light theme.
  - Solid colored containers/buttons (e.g. `.btn-primary`, `.bg-gradient-to-br`) should exclude their nested white text elements using a `:not(...)` filter to preserve their solid-color legibility.
- **Logo and Brand Clickability**: Ensure that the top-left branding elements, "Nexus AI" logo signatures, and footer logos are consistently clickable (`onclick="goToLandingPage()"`), interactive, and trigger smooth scrolling to the top hero section.

## Qwen AI, Qwen API & Qwen Cloud Storage Rules

- **Strict Qwen-Only Mandate**: Do NOT use any services, APIs, libraries, or resources from Google Cloud Vertex AI, Google Cloud Studio, or anything pertaining to Gemini for this project. This project is strictly dedicated to Alibaba Cloud's Qwen AI, Qwen API, and Qwen cloud storage and resources.
- **Qwen API Usage**: All LLM queries, reasoning tasks, and generation tasks must be routed through the Qwen API using the configured model (e.g., `qwen-max` or other Qwen models). Ensure `QwenClient` in `backend/app/agents/qwen_client.py` is utilized for all backend agent requests.
- **Prompt Verification**: If any required configuration variable, API key, or parameter for Qwen API is missing, prompt the user specifically for the missing Qwen API key or configuration before proceeding with any action.
- **Storage Preference**: All cloud storage, assets, and database resources associated with AI or model results must use Qwen's default cloud storage and resources (e.g. Alibaba Cloud Object Storage Service / OSS compatible APIs), strictly avoiding Google Cloud Storage (GCS) or any other Google Cloud databases.
