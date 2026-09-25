"""Cliente de la API con registro de tokens por llamada (base del analisis economico)."""
import json
import threading
import time

import anthropic

from config import MODELOS, cargar_env


class LLM:
    def __init__(self):
        cargar_env()
        self.client = anthropic.Anthropic(max_retries=4)
        self.registro: list[dict] = []
        self._lock = threading.Lock()

    def llamar(self, etapa: str, modelo: str, system: str, contenido: list, schema: dict,
               max_tokens: int = 2000) -> dict:
        """Una llamada con salida JSON garantizada por esquema. Devuelve el dict parseado."""
        m = MODELOS[modelo]
        t0 = time.time()
        r = self.client.messages.create(
            model=m["id"], max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": contenido}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        u = r.usage
        costo = (u.input_tokens * m["usd_in"] + u.output_tokens * m["usd_out"]) / 1_000_000
        with self._lock:
            self.registro.append({
                "etapa": etapa, "modelo": m["id"], "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens, "usd": round(costo, 6),
                "stop_reason": r.stop_reason, "segundos": round(time.time() - t0, 2)})
        if r.stop_reason == "max_tokens":
            raise RuntimeError(f"[{etapa}] respuesta cortada por max_tokens ({max_tokens})")
        texto = next(b.text for b in r.content if b.type == "text")
        return json.loads(texto)

    def resumen(self) -> dict:
        por_etapa: dict[str, dict] = {}
        for c in self.registro:
            e = por_etapa.setdefault(c["etapa"], {"llamadas": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0})
            e["llamadas"] += 1
            e["input_tokens"] += c["input_tokens"]
            e["output_tokens"] += c["output_tokens"]
            e["usd"] = round(e["usd"] + c["usd"], 6)
        return por_etapa
