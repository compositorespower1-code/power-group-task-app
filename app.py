import http.server
import socketserver
import os
import json
import datetime

PORT = int(os.environ.get('PORT', 3000))
BASE_DIR = os.path.dirname(__file__)
TASK_FILE = os.path.join(BASE_DIR, "task.md")
LEADS_FILE = os.path.join(BASE_DIR, "leads.json")
PROMPTS_FILE = os.path.join(BASE_DIR, "prompts.json")
PIPELINE_FILE = os.path.join(BASE_DIR, "pipeline.json")
VENTAS_FILE = os.path.join(BASE_DIR, "ventas.json")
EQUIPO_FILE = os.path.join(BASE_DIR, "equipo.json")
IDEAS_FILE = os.path.join(BASE_DIR, "ideas.json")
POWER_RECORDS_FILE = os.path.join(BASE_DIR, "power_records.json")
CRIS_VELEZ_FILE = os.path.join(BASE_DIR, "cris_velez.json")
TAREAS_APP_FILE = os.path.join(BASE_DIR, "tareas_app.json")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")


def read_json(filepath, default=None):
    if default is None:
        default = []
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
        return default
    except (json.JSONDecodeError, Exception):
        return default


def write_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class TaskHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    # Mapa de rutas GET a archivos JSON
    JSON_ROUTES = {
        '/api/leads': (LEADS_FILE, []),
        '/api/prompts': (PROMPTS_FILE, []),
        '/api/pipeline': (PIPELINE_FILE, {"compositores": [], "producciones": [], "videoclips": []}),
        '/api/ventas': (VENTAS_FILE, {"pipeline": [], "stats": {"month_goal": 0, "month_closed": 0, "revenue_goal": 0, "revenue_actual": 0}}),
        '/api/equipo': (EQUIPO_FILE, []),
        '/api/ideas': (IDEAS_FILE, []),
        '/api/power-records': (POWER_RECORDS_FILE, {"launch_date": "", "milestones": [], "kpis": {}, "notes": ""}),
        '/api/cris-velez': (CRIS_VELEZ_FILE, {"lanzamientos": [], "tareas": [], "notas": ""}),
        '/api/tareas-app': (TAREAS_APP_FILE, {"dia": [], "mes": []}),
    }

    def end_headers(self):
        # Prevent Safari from caching HTML/JS/CSS
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/tasks':
            try:
                with open(TASK_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_json({"content": content})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif self.path in self.JSON_ROUTES:
            filepath, default = self.JSON_ROUTES[self.path]
            data = read_json(filepath, default)
            self.send_json(data)
        else:
            super().do_GET()

    def read_post_body(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    # Mapa de rutas POST a archivos JSON (sobreescritura completa)
    JSON_POST_ROUTES = {
        '/api/pipeline': PIPELINE_FILE,
        '/api/ventas': VENTAS_FILE,
        '/api/equipo': EQUIPO_FILE,
        '/api/ideas': IDEAS_FILE,
        '/api/power-records': POWER_RECORDS_FILE,
        '/api/cris-velez': CRIS_VELEZ_FILE,
        '/api/tareas-app': TAREAS_APP_FILE,
    }

    def do_POST(self):
        if self.path == '/api/tasks':
            data = self.read_post_body()
            try:
                with open(TASK_FILE, 'w', encoding='utf-8') as f:
                    f.write(data['content'])
                self.send_json({"status": "success"})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif self.path == '/api/leads':
            new_lead = self.read_post_body()
            try:
                leads = read_json(LEADS_FILE, [])
                new_lead['time'] = datetime.datetime.now().strftime("%H:%M")
                leads.insert(0, new_lead)
                leads = leads[:10]
                write_json(LEADS_FILE, leads)
                self.send_json({"status": "success"})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif self.path in self.JSON_POST_ROUTES:
            data = self.read_post_body()
            try:
                write_json(self.JSON_POST_ROUTES[self.path], data)
                self.send_json({"status": "success"})
            except Exception as e:
                self.send_json({"error": str(e)})
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TaskHandler) as httpd:
        print(f"Servidor POWER GROUP TASK corriendo en puerto {PORT}")
        print(f"Directorio publico: {PUBLIC_DIR}")
        httpd.serve_forever()
