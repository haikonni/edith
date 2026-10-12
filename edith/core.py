"""Edith - Personal AI Assistant (portable core, imports modules directly)."""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "modules"))

import jarvis_agenda as agenda_mod
import jarvis_saude as saude_mod
import jarvis_enem as enem_mod
import jarvis_produtividade as prod_mod

API_KEY = os.environ.get("OPENROUTER_API_KEY") or ""


class Edith:
    def __init__(self):
        self.data_dir = Path(os.environ.get("EDITH_DATA_DIR", str(Path.home() / "Evolution" / "Edith")))
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_dashboard(self) -> Dict:
        return {
            "agenda": self._get_agenda_summary(),
            "saude": self._get_saude_summary(),
            "estudos": self._get_estudos_summary(),
            "produtividade": self._get_produtividade_summary(),
            "noticias": [],
            "tempo": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def _get_agenda_summary(self) -> Dict:
        try:
            todos = agenda_mod.read_compromissos()
            hoje_str = datetime.now().strftime("%Y-%m-%d")
            hoje = [c for c in todos if c.get("data") == hoje_str and not c.get("feito")]
            return {
                "hoje": [{"hora": c.get("hora") or "", "titulo": c.get("titulo", "")} for c in hoje],
                "proximos": [],
                "total_semana": len(hoje),
            }
        except Exception:
            return {"hoje": [], "proximos": [], "total_semana": 0}

    def _get_saude_summary(self) -> Dict:
        try:
            entries = saude_mod.read_log()
            pesos = [e for e in entries if e.get("tipo") == "peso"]
            peso = pesos[-1]["valor"] if pesos else None
            return {"peso_atual": peso, "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d")}
        except Exception:
            return {"peso_atual": None, "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d")}

    def _get_estudos_summary(self) -> Dict:
        try:
            entries = enem_mod.read_log()
            week_ago = datetime.now().timestamp() - 7 * 86400
            total = sum(
                e.get("valor", 0) for e in entries
                if e.get("tipo") == "estudo"
                and datetime.fromisoformat(e["timestamp"]).timestamp() > week_ago
            )
            return {"horas_semana": round(total, 1), "proxima_revisao": "Redação"}
        except Exception:
            return {"horas_semana": 0, "proxima_revisao": "Redação"}

    def _get_produtividade_summary(self) -> Dict:
        try:
            data = prod_mod.load_tarefas()
            tarefas = data.get("tarefas", [])
            total = len(tarefas)
            completas = sum(1 for t in tarefas if t.get("feito"))
            pct = int((completas / total * 100) if total else 0)
            return {"completas": completas, "total": total, "percentual": pct}
        except Exception:
            return {"completas": 0, "total": 0, "percentual": 0}

    def chat(self, message: str, context: Optional[Dict] = None) -> str:
        dashboard = self.get_dashboard()
        if API_KEY:
            return self._chat_with_ai(message, dashboard)
        return self._mock_response(message, dashboard)

    def _chat_with_ai(self, message: str, dashboard: Dict) -> str:
        try:
            import requests
            ctx = (
                f"Data: {dashboard['tempo']}. "
                f"Compromissos hoje: {len(dashboard['agenda']['hoje'])}. "
                f"Produtividade: {dashboard['produtividade']['percentual']}%. "
                f"Estudo semana: {dashboard['estudos'].get('horas_semana', 0)}h."
            )
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "anthropic/claude-3.5-haiku",
                    "messages": [
                        {"role": "system", "content": "Você é Edith, assistente pessoal. Responda em português brasileiro, útil e concisa."},
                        {"role": "user", "content": f"{ctx}\nUsuário: {message}"},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Erro na API: {e}"
        return "Desculpe, não consegui processar sua mensagem."

    def _mock_response(self, message: str, dashboard: Dict) -> str:
        m = message.lower()
        if "ola" in m or m.strip() in ("oi", "oi edith", "olá"):
            return "Olá Alencar! Sou a Edith, sua assistente pessoal. Como posso ajudar você hoje?"
        if "agenda" in m or "compromisso" in m:
            hoje = dashboard["agenda"]["hoje"]
            if hoje:
                return f"Você tem {len(hoje)} compromisso(s) hoje: " + ", ".join(c["titulo"] for c in hoje[:3])
            return "Não há compromissos hoje. Bom dia livre!"
        if "saude" in m or "saúde" in m or "peso" in m or "treino" in m:
            p = dashboard["saude"]["peso_atual"]
            return f"Seu último peso registrado foi {p}kg. Continue com a rotina de treinos!" if p else "Ainda sem peso registrado. Registre com o módulo de saúde!"
        if "estudo" in m or "enem" in m:
            return f"Você estudou {dashboard['estudos'].get('horas_semana', 0)}h esta semana. Recomendo focar em redação!"
        if "produtividade" in m or "tarefa" in m:
            return f"Você completou {dashboard['produtividade']['percentual']}% das tarefas hoje. Continue assim!"
        return "Estou aqui para ajudar! Posso verificar sua agenda, saúde, estudos ou produtividade. O que você precisa?"


def main():
    edith = Edith()
    if len(sys.argv) < 2:
        print("Uso: python -m edith.core [dashboard|chat 'msg']")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "dashboard":
        print(json.dumps(edith.get_dashboard(), indent=2, ensure_ascii=False, default=str))
    elif cmd == "chat":
        print(edith.chat(" ".join(sys.argv[2:])))
    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
