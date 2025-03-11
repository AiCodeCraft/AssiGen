# Copyright Volkan Sah Kücükbudak 
# Only for academic research! 
import os
config = load_config()
# Matplotlib Cache-Konfiguration für Huggingface Spaces
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib-cache'
os.makedirs(os.environ['MPLCONFIGDIR'], exist_ok=True)

import gradio as gr
import json
from pathlib import Path
from modules.model_handler import AI_MODELS, generate_code
from modules.config_loader import load_config

# Huggingface Spaces-Konfiguration
HF_SPACE = os.getenv('HF_SPACE', False)
TEMP_DIR = Path('/tmp') if HF_SPACE else Path(__file__).parent / 'temp'
TEMP_DIR.mkdir(exist_ok=True)

# UI-Komponenten
def create_interface():
    with gr.Blocks(title="KI-Assistent Generator") as demo:
        gr.Markdown("# 🚀 KI-Assistent Generator")
        
        with gr.Row():
            with gr.Column(scale=2):
                task_input = gr.Textbox(label="Aufgabenbeschreibung", placeholder="Beschreibe deinen gewünschten Assistenten...")
                api_key = gr.Textbox(label="API-Key", type="password")
                language = gr.Dropdown(["python", "php", "javascript"], label="Programmiersprache")
                generate_btn = gr.Button("Generieren", variant="primary")
            
            with gr.Column(scale=3):
                code_output = gr.Code(label="Generierter Code", language="python", interactive=True)
                status = gr.Textbox(label="Status", interactive=False)
        
        generate_btn.click(
            generate_code_wrapper,
            inputs=[task_input, api_key, language],
            outputs=[code_output, status]
        )
        
    return demo

# Hilfsfunktion für Code-Generierung
def generate_code_wrapper(task_input, api_key, language):
    try:
        if not task_input.strip():
            return "", "⚠️ Bitte Aufgabenbeschreibung eingeben!"
        
        if not api_key.strip():
            return "", "🔑 API-Key wird benötigt!"
        
        generated_code = generate_code(
            task_input=task_input,
            api_key=api_key,
            language=language,
            hf_space=HF_SPACE,
            temp_dir=str(TEMP_DIR)
        )
        
        return generated_code, "✅ Code erfolgreich generiert!"
    except Exception as e:
        return "", f"❌ Fehler: {str(e)}"

if __name__ == "__main__":
    config = load_config()
    interface = create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv('PORT', 7860)),
        share=config.get('share', False)
    )
