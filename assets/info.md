### **1. Project Overview & Use Case**
*   **Objective:** To demonstrate **"Creation at Scale"** by converting a dry, text-heavy technical documentation page into an engaging, 11-minute animated video using a multi-agent workflow.
*   **Source Material:** The "Safety and Security for AI Agents" documentation from the **Agent Development Kit (ADK)**.
*   **Constraint:** The workflow must be automated to run in the cloud, avoiding the need to "babysit" the process on a local machine.

### **2. Pre-Production: Asset & Character Generation**
Before the agents take over, the visual foundation is established using **Nano Banana** (Gemini 2.5 Flash Image).

*   **Character:** "Ana Cappy" (An anthropomorphic Capybara).
*   **Style Definition:**
    *   **Animation Style:** Cartoon-like, emulating familiar animation styles.
    *   **Color Palette:** Google ecosystem colors, slightly washed out to match the specific cartoon aesthetic.
    *   **Lighting/Shading:** Specified to define how the character looks in motion (dynamic), not just as a still image.
    *   **Negative Prompts:** Explicit instructions to avoid photorealism or complex 3D textures.
*   **Consistency Tools:**
    *   **Character Bible:** A detailed text description defining the character's name, gender, age, professional background, and wardrobe. This is crucial because **Veo** (the video model) is stateless; detailed prompts prevent "identity drift" (e.g., ensuring a t-shirt doesn't disappear in different shots).
    *   **Environment Design:** The scene (an office setting) was generated separately from the character to maintain control.
    *   **Multi-View Generation (The "Panels"):** instead of one reference image, **Nano Banana** was used to generate **four specific views** (panels) of the character in the environment from different angles. These serve as anchors for the video agent to switch between.

### **3. Production: The Multi-Agent Architecture**
The core production is handled by a system built with the **Agent Development Kit (ADK)** and deployed on **Cloud Run**.

**System Components:**
*   **LLM:** Agents utilize **Gemini 2.5 Pro** for reasoning and task execution.
*   **Storage:** **Google Cloud Storage (GCS)** for persistent storage of video/image artifacts.
*   **State Management:** **Vertex AI Session Service** to allow data sharing between agents.

**Agent Roles:**
The workflow utilizes three distinct agents:

1.  **The Orchestrator (Root Agent):**
    *   Receives the high-level prompt, the character bible, voice descriptions, and the documentation text (with code blocks manually removed).
    *   Manages the flow between the sub-agents.

2.  **The Script Sequencer Agent:**
    *   **Task 1 (Rewrite):** Converts the technical documentation into a natural-sounding script suitable for a narrator (Ana Cappy).
    *   **Task 2 (Chunking):** Slices the script into segments no longer than **8 seconds** (to fit Veo's generation window).
    *   **Task 3 (Direction):** Randomly assigns one of the **four view panels** to each chunk. This simulates professional editing by cutting between different camera angles to maintain visual interest.

3.  **The Video Agent:**
    *   **Task:** Executes the generation for each chunk.
    *   **Mechanism:** Calls a **Media MCP (Model Context Protocol) Server**.
    *   **Generation:** Triggers **Veo 3.1** to generate the video clip using the assigned script chunk, the specific view image, and the style prompts.

### **4. Execution & Human-in-the-Loop**
*   **Scale:** The agent successfully generated **92 individual video chunks** (totaling ~11 minutes).
*   **Review Process:** The user (Vlad Kolesnikov) acted as the director.
    *   *Specific Example:* He reviewed video #49, disliked the specific view chosen by the agent, and instructed the agent to "regenerate with a different view number."
*   **Generation Output:** The agent provided a sequential list of URLs for all 92 video files.

### **5. Post-Production: Automation & Polish**
Once the raw videos were generated, a post-production workflow (aided by AI) was used to finalize the asset.

*   **Validation & Trimming:**
    *   **Problem:** Some script chunks were shorter than 8 seconds, resulting in Veo generating awkward artifacts or idle movement at the end of clips.
    *   **Solution:** **Gemini Flash Lite** was used to analyze the video files and provide timestamps for trimming (cutting out the bad footage).
*   **Assembly:**
    *   **Gemini CLI** was used to write and execute **FFmpeg** commands to concatenate the 92 trimmed videos into a single file.
*   **Audio Replacement (Critical Step):**
    *   **Problem:** While **Veo 3.1** generates expressive audio and lip-syncing, the voice consistency varied slightly across the 92 clips.
    *   **Solution:** **ElevenLabs** was used to regenerate the voice track for 100% consistency and high audio quality.
    *   **Process:** The script was processed through ElevenLabs in 5-minute batches (due to API limits).
    *   **Integration:** **Gemini CLI** was used again to replace the audio track in the final video.
    *   **Result:** The final video retained the *visual* acting and lip movements generated by **Veo** (which are based on the original audio generation) but featured the clean, consistent audio from **ElevenLabs**.

### **6. Resources**
*   **Repository:** The full code for this agent workflow is available in the Google Cloud naming convention repository under the `notebooks` subfolder.
*   **Deployment:** Instructions included for deploying the agent container to **Cloud Run**.