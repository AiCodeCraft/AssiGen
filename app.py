import gradio as gr
import os
import json
from typing import Dict, List, Any
from jinja2 import Template

# Konfigurationen für verschiedene Modelle und APIs
AI_MODELS = {
    "openai": {
        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4o"],
        "import": "from openai import OpenAI",
        "setup": "client = OpenAI(api_key=api_key)",
        "call": """response = client.chat.completions.create(
            model="{model}",
            messages=[
                {{"role": "system", "content": "{system_prompt}"}},
                {{"role": "user", "content": "{user_input}"}}
            ],
            temperature={temperature}
        )
        return response.choices[0].message.content"""
    },
    "deepseek": {
        "models": ["deepseek-coder", "deepseek-chat"],
        "import": "import requests",
        "setup": "headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}",
        "call": """response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json={{
                "model": "{model}",
                "messages": [
                    {{"role": "system", "content": "{system_prompt}"}},
                    {{"role": "user", "content": "{user_input}"}}
                ],
                "temperature": {temperature}
            }}
        )
        return response.json()["choices"][0]["message"]["content"]"""
    },
    "anthropic": {
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "import": "import anthropic",
        "setup": "client = anthropic.Anthropic(api_key=api_key)",
        "call": """response = client.messages.create(
            model="{model}",
            system="{system_prompt}",
            messages=[
                {{"role": "user", "content": "{user_input}"}}
            ],
            temperature={temperature}
        )
        return response.content[0].text"""
    }
}

# Funktionen für die Feature-Handler
FEATURE_HANDLERS = {
    "file_handling": {
        "imports": """import os
import tempfile
from werkzeug.utils import secure_filename""",
        "functions": """def save_uploaded_file(file):
    if file is None:
        return None
    temp_dir = tempfile.mkdtemp()
    filename = secure_filename(file.name)
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(file.read())
    return filepath

def read_file_content(filepath, max_size=100000):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read(max_size)
    return content"""
    },
    "memory": {
        "imports": """import sqlite3
import json""",
        "functions": """class ConversationMemory:
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            session_id TEXT,
            timestamp TEXT,
            user_input TEXT,
            assistant_response TEXT
        )
        ''')
        conn.commit()
        conn.close()
        
    def save_interaction(self, session_id, user_input, assistant_response):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, timestamp, user_input, assistant_response) VALUES (?, datetime('now'), ?, ?)",
            (session_id, user_input, assistant_response)
        )
        conn.commit()
        conn.close()
        
    def get_conversation_history(self, session_id, limit=10):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_input, assistant_response FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (session_id, limit)
        )
        history = cursor.fetchall()
        conn.close()
        return history"""
    },
    "api_integration": {
    "imports": """import requests
    import json"""
    "functions": """def call_external_api(url, method="GET", headers=None, data=None, params=None):"""
    headers = headers or {}

    if method.upper() == "GET":
        response = requests.get(url, headers=headers, params=params)
    elif method.upper() == "POST":
        response = requests.post(url, headers=headers, json=data if data else None, params=params)
    elif method.upper() == "PUT":
        response = requests.put(url, headers=headers, json=data if data else None, params=params)
    elif method.upper() == "DELETE":
        response = requests.delete(url, headers=headers, params=params)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    if response.status_code >= 200 and response.status_code < 300:
        try:
            return response.json()
        except:
            return response.text
    else:
        return {
            "error": True,
            "status_code": response.status_code,
            "message": response.text
        }"""
}

}

def parse_tasks(task_input: str) -> Dict[str, Any]:
    """Parse the task input to determine the required features and configurations."""
    task_input = task_input.lower()
    
    # Bestimme die Programmiersprache
    if "python" in task_input:
        language = "python"
    elif "php" in task_input:
        language = "php"
    elif "javascript" in task_input or "js" in task_input:
        language = "javascript"
    else:
        language = "python"  # Standard
    
    # Bestimme die zu verwendende KI-API
    if "openai" in task_input:
        api = "openai"
    elif "deepseek" in task_input:
        api = "deepseek"
    elif "anthropic" in task_input or "claude" in task_input:
        api = "anthropic"
    else:
        api = "openai"  # Standard
    
    # Bestimme das Modell (falls angegeben)
    model = None
    for model_name in AI_MODELS[api]["models"]:
        if model_name.lower() in task_input:
            model = model_name
            break
    
    if not model:
        model = AI_MODELS[api]["models"][0]  # Verwende das erste Modell als Standard
    
    # Erfasse die gewünschten Features
    features = []
    if any(x in task_input for x in ["file", "files", "upload", "datei", "dateien"]):
        features.append("file_handling")
    if any(x in task_input for x in ["memory", "history", "gedächtnis", "speicher", "verlauf"]):
        features.append("memory")
    if any(x in task_input for x in ["api", "integration", "external", "extern"]):
        features.append("api_integration")
    
    # Erfasse weitere Parameter
    web_ui = "web" in task_input or "ui" in task_input or "interface" in task_input
    cli = "cli" in task_input or "command" in task_input or "terminal" in task_input
    
    return {
        "language": language,
        "api": api,
        "model": model,
        "features": features,
        "web_ui": web_ui,
        "cli": cli
    }

def generate_code(task_input: str, api_key: str) -> str:
    """Generate the complete code for the AI assistant based on the task input."""
    if not api_key.strip():
        return "Bitte geben Sie einen gültigen API-Key ein."
    
    params = parse_tasks(task_input)
    
    # Template-Auswahl basierend auf der Programmiersprache
    if params["language"] == "python":
        return generate_python_code(params, api_key)
    elif params["language"] == "php":
        return generate_php_code(params, api_key)
    elif params["language"] == "javascript":
        return generate_js_code(params, api_key)
    else:
        return f"Die Programmiersprache {params['language']} wird noch nicht unterstützt."

def generate_python_code(params: Dict[str, Any], api_key: str) -> str:
    """Generate Python code for the AI assistant."""
    api_info = AI_MODELS[params["api"]]
    
    imports = [
        "import os",
        "import sys",
        "import json",
        api_info["import"]
    ]
    
    setup_code = [
        "# API-Setup",
        f"api_key = os.environ.get('API_KEY', '{api_key[:3]}...')"  # Zeige nur einen Teil des API-Keys
    ]
    
    assistant_class = [
        "class AIAssistant:",
        "    def __init__(self, api_key):",
        "        self.api_key = api_key",
        f"        {api_info['setup'].replace('api_key', 'self.api_key')}",
        "",
        "    def ask(self, user_input, system_prompt=\"You are a helpful AI assistant.\", temperature=0.7):",
        f"        {api_info['call'].replace('{model}', params['model']).replace('{temperature}', 'temperature')}"
    ]
    
    # Füge Feature-spezifischen Code hinzu
    for feature in params["features"]:
        if feature in FEATURE_HANDLERS:
            imports.append(FEATURE_HANDLERS[feature]["imports"])
            assistant_class.append("")
            assistant_class.append(f"    # {feature.replace('_', ' ').title()} Methods")
            
            # Indent feature functions correctly
            feature_funcs = FEATURE_HANDLERS[feature]["functions"].split("\n")
            if feature != "memory":  # Memory ist eine Klasse, daher anders behandeln
                feature_funcs = ["    " + line for line in feature_funcs]
                assistant_class.extend(feature_funcs)
            else:
                # Füge Memory-Integration zur Assistenten-Klasse hinzu
                assistant_class.append("    def initialize_memory(self, db_path=\"memory.db\"):")
                assistant_class.append("        self.memory = ConversationMemory(db_path)")
                assistant_class.append("")
                assistant_class.append("    def ask_with_memory(self, user_input, session_id, system_prompt=\"You are a helpful AI assistant.\", temperature=0.7):")
                assistant_class.append("        response = self.ask(user_input, system_prompt, temperature)")
                assistant_class.append("        self.memory.save_interaction(session_id, user_input, response)")
                assistant_class.append("        return response")
    
    # Generiere den Haupt-Code basierend auf UI-Anforderungen
    main_code = ["# Hauptfunktion"]
    
    if params["web_ui"]:
        imports.append("import gradio as gr")
        main_code.extend([
            "def create_web_interface():",
            "    assistant = AIAssistant(api_key)",
            "",
            "    def process_query(query, history):",
            "        response = assistant.ask(query)",
            "        history.append((query, response))",
            "        return \"\", history",
            "",
            "    with gr.Blocks() as demo:",
            "        gr.Markdown(f\"## AI Assistant mit {params['model']}\")",
            "",
            "        chatbot = gr.Chatbot()",
            "        msg = gr.Textbox()",
            "        clear = gr.Button(\"Clear\")",
            "",
            "        msg.submit(process_query, [msg, chatbot], [msg, chatbot])",
            "        clear.click(lambda: None, None, chatbot, queue=False)",
            "",
            "    demo.launch()",
            ""
        ])
    
    if params["cli"]:
        main_code.extend([
            "def run_cli():",
            "    assistant = AIAssistant(api_key)",
            "    print(f\"AI Assistant mit {params['model']} bereit. Zum Beenden 'exit' eingeben.\")",
            "",
            "    while True:",
            "        user_input = input(\"\\nFrage: \")",
            "        if user_input.lower() in ['exit', 'quit', 'q']:",
            "            print(\"Auf Wiedersehen!\")",
            "            break",
            "",
            "        response = assistant.ask(user_input)",
            "        print(f\"\\nAssistent: {response}\")",
            ""
        ])
    
    main_code.append("if __name__ == \"__main__\":")
    if params["web_ui"] and params["cli"]:
        main_code.append("    if len(sys.argv) > 1 and sys.argv[1] == '--cli':")
        main_code.append("        run_cli()")
        main_code.append("    else:")
        main_code.append("        create_web_interface()")
    elif params["web_ui"]:
        main_code.append("    create_web_interface()")
    elif params["cli"]:
        main_code.append("    run_cli()")
    else:
        main_code.append("    assistant = AIAssistant(api_key)")
        main_code.append("    response = assistant.ask(\"Hallo, wie geht es dir?\")")
        main_code.append("    print(f\"Antwort: {response}\")")
    
    # Füge Memory-Klassendefinition hinzu, wenn erforderlich
    memory_class = []
    if "memory" in params["features"]:
        memory_class = FEATURE_HANDLERS["memory"]["functions"].split("\n")
    
    # Kombiniere alles zum endgültigen Code
    all_sections = [
        "# Generierter AI Assistant",
        f"# API: {params['api'].upper()}",
        f"# Modell: {params['model']}",
        f"# Features: {', '.join(params['features']) if params['features'] else 'Keine zusätzlichen Features'}",
        "",
        "\n".join(list(dict.fromkeys(imports))),  # Entferne Duplikate
        "",
        "\n".join(setup_code),
        "",
        "\n".join(memory_class) if memory_class else "",
        "",
        "\n".join(assistant_class),
        "",
        "\n".join(main_code)
    ]
    
    return "\n".join(all_sections)

def generate_php_code(params: Dict[str, Any], api_key: str) -> str:
    """Generate PHP code for the AI assistant."""
    # PHP-Code-Generierung (vereinfachte Version)
    php_template = """<?php
    // Generierter AI Assistant
    // API: {api}
    // Modell: {model}
    // Features: {features}

    class AIAssistant {{
        private $api_key;
        private $model;

        public function __construct($api_key, $model) {{
            $this->api_key = $api_key;
            $this->model = $model;
        }}

        public function ask($prompt, $system_prompt = "You are a helpful AI assistant.", $temperature = 0.7) {{
            $url = "https://api.{api_endpoint}/v1/chat/completions";

            $headers = [
                "Content-Type: application/json",
                "Authorization: Bearer " . $this->api_key
            ];

            $data = [
                "model" => $this->model,
                "messages" => [
                    ["role" => "system", "content" => $system_prompt],
                    ["role" => "user", "content" => $prompt]
                ],
                "temperature" => $temperature
            ];

            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

            $response = curl_exec($ch);
            curl_close($ch);

            $response_data = json_decode($response, true);
            return $response_data["choices"][0]["message"]["content"];
        }}

        {feature_methods}
    }}

    // Hauptcode
    $api_key = '{api_key_preview}';
    $assistant = new AIAssistant($api_key, '{model}');

    {main_code}
    ?>"""

    feature_methods = ""
    if "file_handling" in params["features"]:
        feature_methods += """
        public function handleUploadedFile($file) {
            $tempDir = sys_get_temp_dir();
            $filename = basename($file["name"]);
            $filepath = $tempDir . "/" . $filename;

            if (move_uploaded_file($file["tmp_name"], $filepath)) {
                return $filepath;
            }

            return null;
        }

        public function readFileContent($filepath, $maxSize = 100000) {
            if (!file_exists($filepath)) {
                return null;
            }

            return file_get_contents($filepath, false, null, 0, $maxSize);
        }"""

    if "memory" in params["features"]:
        feature_methods += """
        private $db;

        public function initializeMemory($dbPath = "memory.sqlite") {
            $this->db = new SQLite3($dbPath);
            $this->db->exec("CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                user_input TEXT,
                assistant_response TEXT
            )");
        }

        public function askWithMemory($prompt, $sessionId, $systemPrompt = "You are a helpful AI assistant.", $temperature = 0.7) {
            $response = $this->ask($prompt, $systemPrompt, $temperature);

            $stmt = $this->db->prepare("INSERT INTO conversations (session_id, timestamp, user_input, assistant_response) 
                                        VALUES (:session_id, datetime('now'), :user_input, :assistant_response)");
            $stmt->bindValue(':session_id', $sessionId, SQLITE3_TEXT);
            $stmt->bindValue(':user_input', $prompt, SQLITE3_TEXT);
            $stmt->bindValue(':assistant_response', $response, SQLITE3_TEXT);
            $stmt->execute();

            return $response;
        }"""

    # Bestimme den API-Endpunkt basierend auf der API
    api_endpoint = params["api"]
    if params["api"] == "anthropic":
        api_endpoint = "anthropic.com"
    elif params["api"] == "openai":
        api_endpoint = "openai.com"
    else:
        api_endpoint = "deepseek.com"

    # Generiere den Hauptcode basierend auf UI-Anforderungen
    main_code = ""
    if params["web_ui"]:
        main_code += """
    // Web-UI
    if ($_SERVER["REQUEST_METHOD"] == "POST") {
        $user_input = $_POST["user_input"] ?? "";

        if (!empty($user_input)) {
            $response = $assistant->ask($user_input);
            echo json_encode(["response" => $response]);
            exit;
        }
    }

    ?>
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Assistant</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .chat-container { border: 1px solid #ddd; border-radius: 5px; padding: 10px; height: 400px; overflow-y: auto; margin-bottom: 10px; }
            .user-message { background-color: #e6f7ff; padding: 8px; border-radius: 5px; margin-bottom: 10px; }
            .assistant-message { background-color: #f2f2f2; padding: 8px; border-radius: 5px; margin-bottom: 10px; }
            input[type="text"] { width: 80%; padding: 8px; }
            button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>AI Assistant mit <?php echo htmlspecialchars('{model}'); ?></h1>

        <div class="chat-container" id="chatContainer"></div>

        <div>
            <input type="text" id="userInput" placeholder="Stellen Sie eine Frage...">
            <button onclick="sendMessage()">Senden</button>
        </div>

        <script>
            function sendMessage() {
                const userInput = document.getElementById('userInput').value;
                if (!userInput) return;

                // Nachricht des Benutzers anzeigen
                addMessage('user', userInput);
                document.getElementById('userInput').value = '';

                // Anfrage an den Server senden
                fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: 'user_input=' + encodeURIComponent(userInput)
                })
                .then(response => response.json())
                .then(data => {
                    addMessage('assistant', data.response);
                })
                .catch(error => {
                    console.error('Error:', error);
                    addMessage('assistant', 'Es ist ein Fehler aufgetreten.');
                });
            }

            function addMessage(role, content) {
                const chatContainer = document.getElementById('chatContainer');
                const messageDiv = document.createElement('div');
                messageDiv.className = role + '-message';
                messageDiv.textContent = content;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            // Event-Listener für die Enter-Taste
            document.getElementById('userInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>

    <?php
    // Verhindere weitere Ausführung
    exit;"""
    elif params["cli"]:
        main_code += """
    // CLI-Modus
    echo "AI Assistant mit {model} bereit. Zum Beenden 'exit' eingeben.\n";

    while (true) {
        echo "\nFrage: ";
        $userInput = trim(fgets(STDIN));

        if (in_array(strtolower($userInput), ['exit', 'quit', 'q'])) {
            echo "Auf Wiedersehen!\n";
            break;
        }

        $response = $assistant->ask($userInput);
        echo "\nAssistent: " . $response . "\n";
    }"""
    else:
        main_code += """
    // Einfacher Test
    $response = $assistant->ask("Hallo, wie geht es dir?");
    echo "Antwort: " . $response . "\n";"""

    return php_template.format(
        api=params["api"].upper(),
        api_endpoint=api_endpoint,
        model=params["model"],
        features=", ".join(params["features"]) if params["features"] else "Keine zusätzlichen Features",
        feature_methods=feature_methods,
        api_key_preview=api_key[:3] + "...",
        main_code=main_code
    )

def generate_js_code(params: Dict[str, Any], api_key: str) -> str:
    """Generate JavaScript code for the AI assistant."""
    # JavaScript-Code-Generierung (vereinfachte Version)
    js_template = """// Generierter AI Assistant
// API: {api}
// Modell: {model}
// Features: {features}

{imports}

class AIAssistant {{
  constructor(apiKey) {{
    this.apiKey = apiKey;
    this.model = "{model}";
    {setup}
  }}

  async ask(userInput, systemPrompt = "You are a helpful AI assistant.", temperature = 0.7) {{
    {call_code}
  }}
  
  {feature_methods}
}}

{memory_class}

// Hauptcode
{main_code}
"""

    # Importe basierend auf der API und den Features
    imports = []
    
    if params["api"] == "openai":
        imports.append("const OpenAI = require('openai');")
    elif params["api"] == "anthropic":
        imports.append("const Anthropic = require('@anthropic-ai/sdk');")
    else:
        imports.append("const axios = require('axios');")
    
    if "file_handling" in params["features"]:
        imports.append("const fs = require('fs');")
        imports.append("const path = require('path');")
        imports.append("const os = require('os');")
    
    if params["web_ui"]:
        imports.append("const express = require('express');")
        imports.append("const bodyParser = require('body-parser');")
    
    # Setup-Code basierend auf der API
    setup = ""
    if params["api"] == "openai":
        setup = "this.client = new OpenAI({ apiKey: this.apiKey });"
    elif params["api"] == "anthropic":
        setup = "this.client = new Anthropic({ apiKey: this.apiKey });"
    
    # API-Aufruf basierend auf der ausgewählten API
    call_code = ""
    if params["api"] == "openai":
        call_code = """
    try {
      const response = await this.client.chat.completions.create({
        model: this.model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userInput }
        ],
        temperature: temperature
      });
      return response.choices[0].message.content;
    } catch (error) {
      console.error("Error calling OpenAI:", error);
      return "An error occurred while processing your request.";
    }"""
    elif params["api"] == "anthropic":
        call_code = """
    try {
      const response = await this.client.messages.create({
        model: this.model,
        system: systemPrompt,
        messages: [
          { role: "user", content: userInput }
        ],
        temperature: temperature
      });
      return response.content[0].text;
    } catch (error) {
      console.error("Error calling Anthropic:", error);
      return "An error occurred while processing your request.";
    }"""
    else:  # deepseek und andere
        call_code = """
    try {
      const response = await axios.post("https://api.deepseek.com/v1/chat/completions", {
        model: this.model,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userInput }
        ],
        temperature: temperature
      }, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.apiKey}`
        }
      });
      
      return response.data.choices[0].message.content;
    } catch (error) {
      console.error("Error calling API:", error);
      return "An error occurred while processing your request.";
    }"""
    
    # Feature-Methoden
    feature_methods = ""
    
    if "file_handling" in params["features"]:
        feature_methods += """
  saveUploadedFile(fileData, filename) {
    const tempDir = os.tmpdir();
    const filepath = path.join(tempDir, filename);
    
    return new Promise((resolve, reject) => {
      fs.writeFile(filepath, fileData, (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(filepath);
      });
    });
  }
  
  readFileContent(filepath, maxSize = 100000) {
    return new Promise((resolve, reject) => {
      fs.readFile(filepath, 'utf8', (err, data) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(data.slice(0, maxSize));
      });
    });
  }"""
    
    if "memory" in params["features"]:
        feature_methods += """
  initializeMemory(dbPath = "memory.db") {
    this.memory = new ConversationMemory(dbPath);
  }
  
  async askWithMemory(userInput, sessionId, systemPrompt = "You are a helpful AI assistant.", temperature = 0.7) {
    const response = await this.ask(userInput, systemPrompt, temperature);
    await this.memory.saveInteraction(sessionId, userInput, response);
    return response;
  }"""
    
    # Memory-Klasse wenn erforderlich
    memory_class = ""
    if "memory" in params["features"]:
        imports.append("const sqlite3 = require('sqlite3').verbose();")
        
        memory_class = """
class ConversationMemory {
  constructor(dbPath = "memory.db") {
    this.dbPath = dbPath;
    this.initDb();
  }
  
  initDb() {
    this.db = new sqlite3.Database(this.dbPath, (err) => {
      if (err) {
        console.error("Error opening database:", err);
        return;
      }
      
      this.db.run(`CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        user_input TEXT,
        assistant_response TEXT
      )`);
    });
  }
  
  saveInteraction(sessionId, userInput, assistantResponse) {
    return new Promise((resolve, reject) => {
      const stmt = this.db.prepare(
        `INSERT INTO conversations (session_id, user_input, assistant_response) 
         VALUES (?, ?, ?)`
      );
      
      stmt.run(sessionId, userInput, assistantResponse, function(err) {
        if (err) {
          reject(err);
          return;
        }
        resolve(this.lastID);
      });
      
      stmt.finalize();
    });
  }
  
  getConversationHistory(sessionId, limit = 10) {
  

    return new Promise((resolve, reject) => {
      this.db.all(
        `SELECT user_input, assistant_response FROM conversations 
         WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?`,
        [sessionId, limit],
        (err, rows) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(rows);
        }
      );
    });
  }
}"""feature_methods += ""
        initializeMemory(dbPath = "memory.db") {
    this.memory = new ConversationMemory(dbPath);
  }
  
  async askWithMemory(userInput, sessionId, systemPrompt = "You are a helpful AI assistant.", temperature = 0.7) {
    const response = await this.ask(userInput, systemPrompt, temperature);
    await this.memory.saveInteraction(sessionId, userInput, response);
    return response;
  }
        // Hauptcode für den KI-Assistenten
const apiKey = process.env.API_KEY || "abc..."; // API-Key über Umgebungsvariable oder Platzhalter

const assistant = new AIAssistant(apiKey);

if (process.argv.includes("--cli")) {
  // CLI-Modus
  runCli();
} else if (process.argv.includes("--web")) {
  // Web-UI-Modus
  createWebInterface();
} else {
  // Standard-Modus (einfacher Test)
  runTest();
}

async function runTest() {
  try {
    const response = await assistant.ask("Hallo, wie geht es dir?");
    console.log(`Antwort: ${response}`);
  } catch (error) {
    console.error("Fehler beim Test:", error);
  }
}

async function runCli() {
  const readline = require('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  console.log(`AI Assistant mit ${assistant.model} bereit. Zum Beenden 'exit' eingeben.`);
  
  function askQuestion() {
    rl.question("\nFrage: ", async (userInput) => {
      if (["exit", "quit", "q"].includes(userInput.toLowerCase())) {
        console.log("Auf Wiedersehen!");
        rl.close();
        return;
      }
      
      try {
        const response = await assistant.ask(userInput);
        console.log(`\nAssistent: ${response}`);
      } catch (error) {
        console.error("Fehler:", error);
        console.log("\nAssistent: Es ist ein Fehler aufgetreten.");
      }
      
      askQuestion();
    });
  }
  
  askQuestion();
}

function createWebInterface() {
  const app = express();
  const port = process.env.PORT || 3000;
  
  // Middleware
  app.use(bodyParser.json());
  app.use(bodyParser.urlencoded({ extended: true }));
  app.use(express.static('public'));
  
  // HTML für die Startseite
  app.get('/', (req, res) => {
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>AI Assistant</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
          .chat-container { border: 1px solid #ddd; border-radius: 5px; padding: 10px; height: 400px; overflow-y: auto; margin-bottom: 10px; }
          .user-message { background-color: #e6f7ff; padding: 8px; border-radius: 5px; margin-bottom: 10px; }
          .assistant-message { background-color: #f2f2f2; padding: 8px; border-radius: 5px; margin-bottom: 10px; }
          input[type="text"] { width: 80%; padding: 8px; }
          button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; }
        </style>
      </head>
      <body>
        <h1>AI Assistant mit ${assistant.model}</h1>
        
        <div class="chat-container" id="chatContainer"></div>
        
        <div>
          <input type="text" id="userInput" placeholder="Stellen Sie eine Frage...">
          <button onclick="sendMessage()">Senden</button>
        </div>
        
        <script>
          function sendMessage() {
            const userInput = document.getElementById('userInput').value;
            if (!userInput) return;
            
            // Nachricht des Benutzers anzeigen
            addMessage('user', userInput);
            document.getElementById('userInput').value = '';
            
            // Anfrage an den Server senden
            fetch('/ask', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ user_input: userInput })
            })
            .then(response => response.json())
            .then(data => {
              addMessage('assistant', data.response);
            })
            .catch(error => {
              console.error('Error:', error);
              addMessage('assistant', 'Es ist ein Fehler aufgetreten.');
            });
          }
          
          function addMessage(role, content) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = role + '-message';
            messageDiv.textContent = content;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
          }
          
          // Event-Listener für die Enter-Taste
          document.getElementById('userInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
              sendMessage();
            }
          });
        </script>
      </body>
      </html>
    `);
  });
  
  // API-Endpunkt für Anfragen
  app.post('/ask', async (req, res) => {
    try {
      const userInput = req.body.user_input;
      
      if (!userInput) {
        return res.status(400).json({ error: "Keine Eingabe vorhanden" });
      }
      
      const response = await assistant.ask(userInput);
      res.json({ response });
    } catch (error) {
      console.error("Fehler bei der Anfrage:", error);
      res.status(500).json({ error: "Interner Serverfehler" });
    }
  });
  
  // Server starten
  app.listen(port, () => {
    console.log(`Server läuft auf http://localhost:${port}`);
  });
}
