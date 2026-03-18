import http.server
import socketserver
import os
import json
import datetime
import urllib.request
import urllib.parse

PORT = int(os.environ.get('PORT', 3000))
BASE_DIR = os.path.dirname(__file__)
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# Supabase config
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')


def supabase_read(key, default=None):
    """Read data from Supabase app_data table by key."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return default
    try:
        url = f"{SUPABASE_URL}/rest/v1/app_data?key=eq.{urllib.parse.quote(key)}&select=data"
        req = urllib.request.Request(url)
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode())
            if rows and 'data' in rows[0]:
                return rows[0]['data']
        return default
    except Exception as e:
        print(f"[Supabase READ error] key={key}: {e}")
        return default


def supabase_write(key, data):
    """Write data to Supabase app_data table by key."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    try:
        url = f"{SUPABASE_URL}/rest/v1/app_data?key=eq.{urllib.parse.quote(key)}"
        body = json.dumps({
            "key": key,
            "data": data,
            "updated_at": datetime.datetime.now().isoformat()
        }).encode()
        req = urllib.request.Request(url, data=body, method='PATCH')
        req.add_header('apikey', SUPABASE_KEY)
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Prefer', 'return=minimal')
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
        return True
    except Exception as e:
        print(f"[Supabase WRITE error] key={key}: {e}")
        return False


# Mapa de rutas API a keys de Supabase + defaults
ROUTE_MAP = {
    '/api/leads':         ('leads', []),
    '/api/prompts':       ('prompts', []),
    '/api/pipeline':      ('pipeline', {"compositores": [], "producciones": [], "videoclips": []}),
    '/api/ventas':        ('ventas', {"pipeline": [], "stats": {"month_goal": 0, "month_closed": 0, "revenue_goal": 0, "revenue_actual": 0}}),
    '/api/equipo':        ('equipo', []),
    '/api/ideas':         ('ideas', []),
    '/api/power-records': ('power_records', {"launch_date": "", "milestones": [], "kpis": {}, "notes": ""}),
    '/api/cris-velez':    ('cris_velez', {"lanzamientos": [], "tareas": [], "notas": ""}),
    '/api/tareas-app':    ('tareas_app', {"semana": [], "mes": [], "ano12": []}),
}

# Rutas que aceptan POST (sobreescritura completa)
POST_ROUTES = {
    '/api/pipeline', '/api/ventas', '/api/equipo', '/api/ideas',
    '/api/power-records', '/api/cris-velez', '/api/tareas-app',
}


class TaskHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/tasks':
            data = supabase_read('tasks', {"content": ""})
            self.send_json(data)
        elif self.path in ROUTE_MAP:
            key, default = ROUTE_MAP[self.path]
            data = supabase_read(key, default)
            self.send_json(data)
        else:
            super().do_GET()

    def read_post_body(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def do_POST(self):
        if self.path == '/api/tasks':
            data = self.read_post_body()
            try:
                supabase_write('tasks', data)
                self.send_json({"status": "success"})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif self.path == '/api/leads':
            new_lead = self.read_post_body()
            try:
                leads = supabase_read('leads', [])
                new_lead['time'] = datetime.datetime.now().strftime("%H:%M")
                leads.insert(0, new_lead)
                leads = leads[:10]
                supabase_write('leads', leads)
                self.send_json({"status": "success"})
            except Exception as e:
                self.send_json({"error": str(e)})
        elif self.path in POST_ROUTES and self.path in ROUTE_MAP:
            data = self.read_post_body()
            try:
                key, _ = ROUTE_MAP[self.path]
                supabase_write(key, data)
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
    print(f"Supabase URL: {SUPABASE_URL[:30]}..." if SUPABASE_URL else "WARNING: SUPABASE_URL not set!")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), TaskHandler) as httpd:
        print(f"Servidor POWER GROUP TASK corriendo en puerto {PORT}")
        print(f"Directorio publico: {PUBLIC_DIR}")
        httpd.serve_forever()
