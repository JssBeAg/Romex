"""
A small stand-in for INEGI's web service, for development and the browser tests (the real one
needs internet). It answers the same two routes with the 32 states and a few municipalities:

    python manage.py inegi_falso            # http://localhost:8777
    INEGI_API_URL=http://localhost:8777 python manage.py runserver
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from django.core.management.base import BaseCommand

STATES = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Coahuila de Zaragoza", "Colima", "Chiapas", "Chihuahua", "Ciudad de México", "Durango",
    "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "México", "Michoacán de Ocampo", "Morelos",
    "Nayarit", "Nuevo León", "Oaxaca", "Puebla", "Querétaro", "Quintana Roo", "San Luis Potosí",
    "Sinaloa", "Sonora", "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz de Ignacio de la Llave",
    "Yucatán", "Zacatecas",
]
MUNICIPALITIES = {
    "Coahuila de Zaragoza": ["Monclova", "Saltillo", "Torreón"],
    "Jalisco": ["Guadalajara", "Tlaquepaque", "Zapopan"],
    "Nuevo León": ["Apodaca", "Monterrey", "San Pedro Garza García"],
}


def state_rows():
    return [{"cvegeo": f"{i:02d}", "cve_ent": f"{i:02d}", "nomgeo": n} for i, n in enumerate(STATES, 1)]


def municipality_rows(key):
    name = STATES[int(key) - 1]
    names = MUNICIPALITIES.get(name, [f"Municipio de {name}"])
    return [
        {"cvegeo": f"{key}{i:03d}", "cve_ent": key, "cve_mun": f"{i:03d}", "nomgeo": n}
        for i, n in enumerate(names, 1)
    ]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = [p for p in self.path.split("?")[0].split("/") if p]
        try:
            if parts[-1] == "mgee":
                rows = state_rows()
            elif parts[-2] == "mgem":
                rows = municipality_rows(parts[-1])
            else:
                raise ValueError
        except (IndexError, ValueError):
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"datos": rows}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class Command(BaseCommand):
    help = "Levanta un servidor que imita el servicio del INEGI (solo desarrollo y pruebas)."

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8777)

    def handle(self, *args, **options):
        self.stdout.write(f"INEGI falso en http://localhost:{options['port']}")
        ThreadingHTTPServer(("127.0.0.1", options["port"]), Handler).serve_forever()
