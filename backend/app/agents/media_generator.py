"""
Media Generator Agent
Backed by Qwen, formulates visual diffusion prompts, graphic styles, audio scripts, and storyboards.
Mocks native Alibaba Cloud OSS URLs for asset links.
"""
import logging
from datetime import datetime
from typing import Dict, Any
from app.agents.qwen_client import qwen_client, clean_and_parse_json

logger = logging.getLogger(__name__)


class MediaGeneratorAgent:
    """Formulates multimodal asset descriptions, visual diffusion prompts, typography styles, and storyboards."""
    
    def __init__(self, db, workspace_id: str):
        self.db = db
        self.workspace_id = workspace_id
        
    def generate_multimodal_assets(self, title: str, media_type: str, platform: str) -> Dict[str, Any]:
        """
        Generates production-grade design prompts and media specifications.
        Returns visual guidelines, voiceover audio scripts, video storyboards, and Alibaba Cloud OSS URLs.
        """
        prompt = f"""You are a senior Multimodal Creative & Media Director AI.
Your job is to generate full media asset specifications for a post:

Title: "{title}"
Media Type expected: {media_type} (IMAGE, AUDIO, VIDEO)
Platform: {platform}

Generate the asset details and return a JSON object with:
1. media_type: string ('IMAGE', 'AUDIO', or 'VIDEO')
2. image_prompt: string (hyper-detailed diffusion prompt for stable diffusion or midjourney)
3. graphic_concept: string (specifies composition, grid, color palettes using sleek neutral grey-black and active blues, typography)
4. audio_script: string (podcaster/voiceover script with sound effect directions if AUDIO or VIDEO, else null)
5. video_storyboard: string (step-by-step camera directions and visual transitions if VIDEO, else null)
6. asset_url: string (an Alibaba Cloud OSS-compatible bucket URL mockup: https://oss-eu-central.aliyuncs.com/nexus-ai-media/assets/...)

Ensure the output is strictly valid JSON."""

        response = qwen_client.chat_completion([
            {"role": "system", "content": "You are a multimodal creative director skilled in image synthesis, scriptwriting, and video production."},
            {"role": "user", "content": prompt}
        ])
        
        raw_content = response["choices"][0]["message"]["content"]
        parsed = clean_and_parse_json(raw_content)
        thinking = response["choices"][0]["message"].get("reasoning_content", "")
        
        return {
            "status": "success",
            "media_assets": parsed,
            "thinking": thinking,
            "tokens_used": response.get("usage", {}).get("total_tokens", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
