from jinja2 import Environment, FileSystemLoader
import os

AI_MODELS = {
    # Deine Modelldefinitionen hier (wie zuvor)
}

def render_template(template_name, context):
    env = Environment(
        loader=FileSystemLoader('templates'),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template(template_name)
    return template.render(context)

def generate_code(task_input, api_key, language, hf_space=False, temp_dir='/tmp'):
    params = parse_tasks(task_input)  # Deine bestehende Parse-Logik
    
    context = {
        "params": params,
        "api_key": api_key,
        "hf_space": hf_space,
        "temp_dir": temp_dir,
        "model_config": AI_MODELS[params['api']]
    }
    
    return render_template(f"{language}.jinja2", context)
