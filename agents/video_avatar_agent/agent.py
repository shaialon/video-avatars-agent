# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import mimetypes
import os
from pathlib import Path

import google.auth
from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.adk.models.llm_request import LlmRequest
from google.adk.tools import AgentTool

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id) # type: ignore
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

from subagents import script_sequencer_agent, video_agent
from utils.storage_utils import upload_data_to_gcs

# Cache for default view URLs (uploaded from assets folder)
_default_view_urls: list[str] = []


async def _upload_default_views() -> list[str]:
    """Upload default view images from assets folder to GCS."""
    global _default_view_urls
    if _default_view_urls:
        return _default_view_urls
    
    assets_dir = Path(__file__).parent.parent.parent / "assets"
    view_files = sorted(assets_dir.glob("view*.jpeg"))
    
    if not view_files:
        print("Warning: No view images found in assets folder")
        return []
    
    urls = []
    for view_file in view_files:
        data = view_file.read_bytes()
        mime_type = mimetypes.guess_type(str(view_file))[0] or "image/jpeg"
        url = await upload_data_to_gcs("default_views", data, mime_type)
        urls.append(url)
        print(f"Uploaded default view: {view_file.name} -> {url}")
    
    _default_view_urls = urls
    return urls


async def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest
) -> LlmResponse | None:
    """The callback that ensures uploading user's images to GCS."""
    persona_views_urls = callback_context.state.get("persona_views", [])
    remove_indexes = []

    upload_persona_views = len(persona_views_urls) == 0

    user_content = llm_request.contents[0]
    for index, part in enumerate(user_content.parts): # type: ignore
        inline_data = part.inline_data
        if (
            not inline_data
            or not inline_data.data
            or not inline_data.mime_type
        ):
            continue
        if inline_data.mime_type.startswith("image/"):
            if upload_persona_views:
                image_url = await upload_data_to_gcs(
                    callback_context.agent_name,
                    inline_data.data,
                    inline_data.mime_type
                )
                persona_views_urls.append(image_url)
            remove_indexes.append(index)
    remove_indexes.reverse()
    for index in remove_indexes:
        user_content.parts.pop(index) # type: ignore
    
    # If no images were provided, use default views from assets folder
    if upload_persona_views and len(persona_views_urls) == 0:
        persona_views_urls = await _upload_default_views()
    
    user_content.parts.append( # type: ignore
        types.Part.from_text(
            text="## VIEW IMAGE URLS\n" + "\n - ".join(
                f"View {i+1}: {url}" for i, url in enumerate(persona_views_urls)
            )
        )
    )
    if upload_persona_views and persona_views_urls:
        callback_context.state["persona_views"] = persona_views_urls


root_agent = LlmAgent(
    name="root_agent",
    model="gemini-2.5-pro",
    instruction="""
    You are a video generation agent for avatar-based training videos. You orchestrate the creation of videos.
    Your input is a character description, a script, and a set of views of the character.

    **Steps**:

    1. Start with `script_sequencer_agent`. It will split the script into smaller chunks and assign a view number to each chunk.
    2. For each script chunk, use `video_agent` to create a video segment.
    3. Present intermediate and final results to the user. The final result must be a numbered list of all videos in the order of the respective script chunks.

    **Rules:**

    -   Make sure to pass the entire Character Description and Video Shot Instructions to `video_agent` tool.
    -   Pass view image URL and view number to `video_agent` tool.
    -   You must present each generated video segment to the user, right after it is generated. Include the video url, the respective chunk number and the script chunk text in the message,
    -   When output "gs://" URIs to the user, replace "gs://" with "https://storage.mtls.cloud.google.com/".
        When calling any functions/tools, keep "gs://" URIs as they are.
    """.strip(),
    tools=[AgentTool(script_sequencer_agent), AgentTool(video_agent)],
    before_model_callback=before_model_callback,
)
