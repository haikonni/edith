#!/usr/bin/env python3
"""
Edith - Personal AI Assistant
Interface tipo Jarvis para a vida do Alencar: agenda, saúde, ENEM, produtividade.
v2: leitura direta dos módulos (sem subprocess), ações de escrita, chat com
intenções que executam de verdade, dados reais em todas as respostas.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, '/opt/data/scripts')
import jarvis_agenda as agenda_mod
import jarvis_saude as saude_mod
import jarvis_enem as enem_mod
import jarvis_produtividade as prod_mod

# Os módulos notificam via Telegram com token placeholder a cada ação.
# Silencia para não travar (timeout curl) nem spammar: o retorno continua igual.
for _m in (agenda_mod, saude_mod, enem_mod, prod_mod):
    if hasattr(_m, 'send_telegram'):
        setattr(_m, 'send_telegram', lambda *a, **k: False)

DATA_DIR = Path.home() / "Evolution" / "Edith"
API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("FIREWORKS_API_KEY") or ""

MATERIAS_ALIAS = {
    "matemática": "matematica", "matematica": "matematica", "mat": "matematica",
    "português": "portugues", "portugues": "portuguesa", "port": "portugues",
    "redação": "redacao", "redacao": "redacao",
    "história": "historia", "historia": "historia",
    "geografia": "geografia", "geo": "geografia",
    "física": "fisica", "fisica": "fisica",
    "química": "quimica", "quimica": "quimica",
    "biologia": "biologia", "bio": "biologia",
    "filosofia": "filosofia", "filo": "filosofia",
    "sociologia": "sociologia", "socio": "sociologia",
    "inglês": "geral", "ingles": "geral",
}


class Edith:
    """Assistente pessoal Edith."""

    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memoria_file = self.data_dir / "memoria.jsonl"

    # ---------- Memória (tudo que você manda fica salvo) ----------

    @staticmethod
    def limpar_fala(texto: str) -> str:
        """Texto limpo para a voz: sem emojis/símbolos, sem citar formatação."""
        import unicodedata
        t = re.sub(r'[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]', '', texto)
        t = re.sub(r'[*_~`#>|]', '', t)
        t = re.sub(r'https?://\S+', 'link', t)
        t = re.sub(r'[ \t]+', ' ', t)
        t = re.sub(r'\n{3,}', '\n\n', t)
        return unicodedata.normalize('NFC', t).strip()

    def registrar_memoria(self, tipo: str, texto: str, extra: Optional[Dict] = None) -> None:
        try:
            reg = {"ts": datetime.now().isoformat(timespec="seconds"),
                   "tipo": tipo, "texto": texto}
            if extra:
                reg.update(extra)
            with open(self.memoria_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def salvar_lembrete(self, texto: str) -> str:
        texto = (texto or "").strip()
        if not texto:
            return "Nada para salvar na memória."
        self.registrar_memoria("lembrete", texto)
        return f"Salvo na minha memória: {texto}"

    def listar_memoria(self, limite: int = 20) -> List[Dict]:
        try:
            linhas = self.memoria_file.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        out = []
        for ln in linhas[-limite:]:
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
        return list(reversed(out))

    # ---------- Dashboard (leitura direta, sem subprocess) ----------

    def get_dashboard(self) -> Dict:
        return {
            "agenda": self._get_agenda_summary(),
            "saude": self._get_saude_summary(),
            "estudos": self._get_estudos_summary(),
            "produtividade": self._get_produtividade_summary(),
            "tempo": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    def _get_agenda_summary(self) -> Dict:
        try:
            todos = agenda_mod.read_compromissos()
        except Exception:
            todos = []
        hoje_str = datetime.now().strftime("%Y-%m-%d")
        limite = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        hoje = [c for c in todos if c.get("data") == hoje_str and not c.get("feito")]
        proximos = sorted(
            [c for c in todos if hoje_str < str(c.get("data", "")) <= limite and not c.get("feito")],
            key=lambda c: (c.get("data", ""), c.get("hora") or ""),
        )
        fmt = lambda c: {"id": c.get("id"), "hora": c.get("hora") or "",
                         "titulo": c.get("titulo", ""), "data": c.get("data", ""),
                         "categoria": c.get("categoria", "geral")}
        return {"hoje": [fmt(c) for c in hoje],
                "proximos": [fmt(c) for c in proximos[:10]],
                "total_semana": len(hoje) + len(proximos)}

    def _get_saude_summary(self) -> Dict:
        try:
            entries = saude_mod.read_log()
        except Exception:
            entries = []
        peso = next((e["valor"] for e in reversed(entries) if e.get("tipo") == "peso"), None)
        treino = next((e for e in reversed(entries) if e.get("tipo") == "treino"), None)
        sono = next((e.get("valor") for e in reversed(entries) if e.get("tipo") == "sono"), None)
        hoje_str = datetime.now().strftime("%Y-%m-%d")
        comidas_hoje = [e for e in entries
                        if e.get("tipo") == "comida" and str(e.get("timestamp", ""))[:10] == hoje_str]
        kcal_hoje = sum(e.get("kcal") or 0 for e in comidas_hoje)
        return {"peso_atual": peso,
                "ultimo_treino": ({k: treino.get(k) for k in ("valor", "duracao", "timestamp")} if treino else None),
                "ultimo_sono": sono,
                "refeicoes_hoje": len(comidas_hoje),
                "kcal_hoje": kcal_hoje,
                "ultima_atualizacao": datetime.now().strftime("%Y-%m-%d")}

    def _get_estudos_summary(self) -> Dict:
        try:
            entries = enem_mod.read_log()
        except Exception:
            entries = []
        week_ago = datetime.now().timestamp() - 7 * 86400
        por_materia: Dict[str, float] = {}
        total = 0.0
        for e in entries:
            if e.get("tipo") != "estudo":
                continue
            try:
                ts = datetime.fromisoformat(e["timestamp"]).timestamp()
            except Exception:
                continue
            if ts > week_ago:
                m = e.get("materia", "geral")
                por_materia[m] = por_materia.get(m, 0) + (e.get("valor") or 0)
                total += e.get("valor") or 0
        sugestao = next((m for m in enem_mod.MATERIAS if m not in por_materia),
                        min(por_materia, key=por_materia.get) if por_materia else "redacao")
        return {"horas_semana": round(total, 1),
                "por_materia": {k: round(v, 1) for k, v in por_materia.items()},
                "proxima_revisao": sugestao}

    def _get_produtividade_summary(self) -> Dict:
        try:
            data = prod_mod.load_tarefas()
            hoje = datetime.now().strftime("%Y-%m-%d")
            if data.get("data") != hoje:  # reseta chamando a função do módulo
                prod_mod.checklist_diario.__wrapped__ if hasattr(prod_mod.checklist_diario, "__wrapped__") else None
                data = {"tarefas": prod_mod.TAREFAS_PADRAO, "data": hoje}
                prod_mod.save_tarefas(data)
            tarefas = data.get("tarefas", [])
        except Exception:
            tarefas = []
        total = len(tarefas)
        completas = sum(1 for t in tarefas if t.get("feito"))
        return {"completas": completas, "total": total,
                "percentual": int(completas / total * 100) if total else 0,
                "tarefas": [{"id": t.get("id"), "texto": t.get("texto"),
                             "feito": bool(t.get("feito"))} for t in tarefas]}

    # ---------- Ações de escrita ----------

    def acao_add_compromisso(self, titulo: str, data: str, hora: str = None,
                             categoria: str = "geral", nota: str = None) -> str:
        try:
            datetime.strptime(data, "%Y-%m-%d")
        except Exception:
            return "❌ Data inválida. Use o formato AAAA-MM-DD (ex: 2026-10-15)."
        return agenda_mod.add_compromisso(titulo=titulo, data=data, hora=hora,
                                          categoria=categoria, nota=nota)

    def acao_marcar_tarefa(self, id_tarefa: int) -> str:
        try:
            return prod_mod.marcar_tarefa(int(id_tarefa))
        except Exception as e:
            return f"❌ Não achei a tarefa {id_tarefa}. ({e})"

    def acao_peso(self, kg: float) -> str:
        return saude_mod.registrar_peso(float(kg))

    def acao_treino(self, tipo: str, duracao: int = 60) -> str:
        return saude_mod.registrar_treino(tipo, int(duracao))

    def acao_sono(self, horas: float) -> str:
        return saude_mod.registrar_sono(float(horas))

    def acao_comida(self, descricao: str, kcal: int = None) -> str:
        return saude_mod.registrar_comida(descricao, kcal=kcal)

    def acao_estudo(self, horas: float, materia: str = "geral") -> str:
        return enem_mod.registrar_estudo(float(horas), materia)

    # ---------- Chat ----------

    def chat(self, message: str, context: Optional[Dict] = None) -> str:
        msg = (message or "").strip()
        if msg:
            low = msg.lower()
            m = re.search(r'(?:lembre(?:te)?(?:-se)?(?: de)?|guarde(?: na memória)?|anote|salve na memória|memorize)\s*[:\-]?\s*(.+)', low, re.S)
            if m and m.group(1).strip():
                original = re.sub(r'(?i)^(lembre(?:te)?(?:-se)?(?: de)?|guarde(?: na memória)?|anote|salve na memória|memorize)\s*[:\-]?\s*', '', msg).strip()
                return self.salvar_lembrete(original)
            if re.search(r'\b(minha memória|o que você lembra|o que voce lembra|lembranças|lembrancas)\b', low):
                mems = self.listar_memoria(10)
                if not mems:
                    return "Minha memória está vazia por enquanto. Diga 'lembrete: ...' que eu guardo."
                return "O que guardo na memória:\n" + "\n".join(
                    f"• {m.get('ts','')[:16].replace('T',' ')} — {m.get('texto','')}" for m in mems)
        try:
            resp = self._chat_with_ai(msg) if API_KEY else self._smart_response(msg)
        except Exception as e:
            resp = f"Erro na IA: {e}"
        if msg:
            self.registrar_memoria("conversa", msg, {"resposta": (resp or "")[:500]})
        return resp

    def _chat_with_ai(self, message: str) -> str:
        import requests
        d = self.get_dashboard()
        ctx = (f"Data: {d['tempo']}. Compromissos hoje: {len(d['agenda']['hoje'])}. "
               f"Produtividade: {d['produtividade']['percentual']}%. "
               f"Peso: {d['saude']['peso_atual']}kg. Estudo semana: {d['estudos']['horas_semana']}h.")
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": "anthropic/claude-3.5-haiku",
                  "messages": [
                      {"role": "system", "content": "Você é Edith, assistente pessoal do Alencar. Responda útil e concisa em pt-BR."},
                      {"role": "user", "content": f"{ctx}\n\nUsuário: {message}"}],
                  "max_tokens": 500, "temperature": 0.7},
            timeout=30)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return "Desculpe, não consegui processar sua mensagem."

    def _smart_response(self, message: str) -> str:
        """Responde com dados reais e executa ações por intenção."""
        msg = message.strip()
        low = msg.lower()
        d = self.get_dashboard()

        # --- AÇÕES: agenda ---
        if re.search(r'\b(agendar|agende|adicionar compromisso|novo compromisso|marcar compromisso)\b', low):
            return self._intent_agendar(msg, low)
        m = re.search(r'\b(concluir|marcar|feita|feito|pronta|pronto)\b.*?\b(?:tarefa\s*)?(\d{1,2})\b', low)
        if not m:
            m = re.search(r'\btarefa\s*(\d{1,2})\b', low)
        if m and any(w in low for w in ("concluir", "marcar", "feit", "pront", "tarefa", "check")):
            return self.acao_marcar_tarefa(int(m.group(2) if m.lastindex == 2 else m.group(1)))

        # --- AÇÕES: saúde ---
        if re.search(r'\b(registrar peso|pesei|meu peso é|peso atual|atualiza.*peso)\b', low) or \
           (re.search(r'\bpeso\b', low) and re.search(r'\d', low)):
            m = re.search(r'(\d{2,3}(?:[.,]\d{1,2})?)\s*(?:kg)?\b', low)
            if m and not re.search(r'\b(qual|quanto|como está|como esta)\b', low):
                return self.acao_peso(m.group(1).replace(",", "."))
        if re.search(r'\b(fiz treino|registrar treino|treinei|treino de|treino:)\b', low):
            m = re.search(r'treino\s+(?:de\s+)?([a-zà-ú]+)(?:\s+(\d{1,3}))?', low)
            tipo = m.group(1) if m else "geral"
            dur = m.group(2) if m and m.group(2) else 60
            return self.acao_treino(tipo, int(dur))
        if re.search(r'\b(dormi|sono de|registrar sono)\b', low):
            m = re.search(r'(\d(?:[.,]\d)?)\s*h?', low)
            if m:
                return self.acao_sono(m.group(1).replace(",", "."))
        if re.search(r'\b(comi|almocei|jantei|lanchei|tomei café|tomei cafe)\b', low):
            desc = re.sub(r'^(eu\s+)?(comi|almocei|jantei|lanchei)\s+', '', msg, flags=re.I).strip() or msg
            m = re.search(r'(\d{2,5})\s*kcal', low)
            return self.acao_comida(desc, kcal=int(m.group(1)) if m else None)

        # --- AÇÕES: estudos ---
        if re.search(r'\b(estudei|registrar estudo|estudar)\b', low) and re.search(r'\d', low):
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*h', low)
            if m:
                horas = float(m.group(1).replace(",", "."))
                mat = next((v for k, v in MATERIAS_ALIAS.items() if k in low), "geral")
                return self.acao_estudo(horas, mat)

        # --- CONSULTAS (dados reais) ---
        if re.search(r'\b(olá|ola|oi|opa|bom dia|boa tarde|boa noite|e aí|e ai)\b', low) and len(low) < 25:
            return ("Olá Alencar! Sou a Edith. 👋\n"
                    f"Hoje você tem {len(d['agenda']['hoje'])} compromisso(s), "
                    f"{d['produtividade']['percentual']}% das tarefas feitas e "
                    f"{d['estudos']['horas_semana']}h de estudo na semana. O que vamos fazer?")
        if re.search(r'\bagenda\b|\bcompromisso', low):
            return self._resp_agenda(d)
        if re.search(r'\bpeso\b|\bsaúde\b|\bsaude\b|\btreino\b|\bkcal\b|\bcomi\b', low):
            return self._resp_saude(d)
        if re.search(r'\bestud|\benem\b|\bredação\b|\bredacao\b|\bsimulado\b', low):
            return self._resp_estudos(d)
        if re.search(r'\bprodutividade\b|\btarefa', low):
            return self._resp_prod(d)
        return ("Estou aqui para ajudar! Posso: 📅 agendar ('agendar dentista amanhã 14:00'), "
                "✅ marcar tarefas ('concluir tarefa 2'), 💪 registrar peso/treino/sono/comida, "
                "📚 registrar estudo ('estudei 2h matemática'). O que você precisa?")

    def _intent_agendar(self, msg: str, low: str) -> str:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', msg)
        data = m.group(1) if m else None
        if not data:
            m = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', msg)
            if m:
                dd, mm = int(m.group(1)), int(m.group(2))
                yy = int(m.group(3)) if m.group(3) else datetime.now().year
                if yy < 100:
                    yy += 2000
                data = f"{yy:04d}-{mm:02d}-{dd:02d}"
        if not data:
            if "amanh" in low:
                data = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            elif "hoje" in low:
                data = datetime.now().strftime("%Y-%m-%d")
        m = re.search(r'(\d{1,2})[h:](\d{2})', low)
        if not m:
            m = re.search(r'\b(?:às|as)\s*(\d{1,2})\s*h\b', low)
            hora = f"{int(m.group(1)):02d}:00" if m else None
        else:
            hora = f"{int(m.group(1)):02d}:{m.group(2)}"
        titulo = msg
        for pat in [r'(?i)\b(agendar|agende|adicionar compromisso|novo compromisso|marcar compromisso)\b',
                    r'\d{4}-\d{2}-\d{2}', r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',
                    r'(?i)\b(amanhã|amanha|hoje)\b', r'\d{1,2}[h:]\d{2}',
                    r'(?i)\bàs\s*\d{1,2}\s*h\b', r'(?i)\bàs\s*\d{1,2}\b']:
            titulo = re.sub(pat, ' ', titulo)
        titulo = re.sub(r'\s+', ' ', titulo).strip(' -,.')
        if not data:
            return "📅 Entendi! Para qual data? (ex: 'agendar dentista 2026-10-15 14:00' ou 'agendar dentista amanhã 14:00')"
        if not titulo:
            return "📅 Data anotada! Qual o título do compromisso?"
        return self.acao_add_compromisso(titulo=titulo, data=data, hora=hora)

    def _resp_agenda(self, d: Dict) -> str:
        hoje = d["agenda"]["hoje"]
        prox = d["agenda"]["proximos"]
        if not hoje and not prox:
            return "📅 Agenda livre! Nenhum compromisso nos próximos 7 dias. Quer agendar algo?"
        out = ""
        if hoje:
            out += f"📅 Hoje ({len(hoje)}):\n" + "\n".join(
                f"• {c['hora'] or '--:--'} — {c['titulo']}" for c in hoje)
        if prox:
            out += ("\n" if out else "") + "\n📆 Próximos:\n" + "\n".join(
                f"• {c['data'][5:][::-1].replace('-', '/') if False else c['data']} {c['hora'] or ''} — {c['titulo']}".strip()
                for c in prox[:5])
        return out

    def _resp_saude(self, d: Dict) -> str:
        s = d["saude"]
        peso = f"{s['peso_atual']}kg" if s["peso_atual"] else "não registrado"
        t = s["ultimo_treino"]
        treino = f"{t['valor']} ({t['duracao']}min)" if t else "nenhum registrado"
        return (f"💪 Peso: {peso}\n🏋️ Último treino: {treino}\n"
                f"😴 Último sono: {s['ultimo_sono'] or '--'}h\n"
                f"🍽️ Hoje: {s['refeicoes_hoje']} refeição(ões), {s['kcal_hoje']} kcal")

    def _resp_estudos(self, d: Dict) -> str:
        e = d["estudos"]
        det = ", ".join(f"{k}: {v}h" for k, v in sorted(e["por_materia"].items())) or "nada ainda"
        return (f"📚 Semana: {e['horas_semana']}h\n{det}\n"
                f"🎯 Sugestão: focar em {e['proxima_revisao']} (menos estudada)")

    def _resp_prod(self, d: Dict) -> str:
        p = d["produtividade"]
        pend = [f"{t['id']}. {t['texto']}" for t in p["tarefas"] if not t["feito"]][:5]
        out = f"✅ {p['completas']}/{p['total']} tarefas ({p['percentual']}%)"
        if pend:
            out += "\n⬜ Pendentes:\n" + "\n".join(pend)
            out += "\n\nDiga 'concluir tarefa N' que eu marco pra você!"
        else:
            out += "\n🔥 Tudo concluído!"
        return out


def main():
    edith = Edith()
    if len(sys.argv) < 2:
        print("Edith - Personal AI Assistant")
        print("  edith.py dashboard | chat 'msg' | agenda | saude | estudos | produtividade")
        print("  edith.py agendar 'titulo' YYYY-MM-DD [HH:MM] | tarefa <id> | peso <kg> | estudo <h> <materia>")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "dashboard":
        print(json.dumps(edith.get_dashboard(), indent=2, ensure_ascii=False, default=str))
    elif cmd == "chat":
        print(edith.chat(" ".join(sys.argv[2:]) if len(sys.argv) > 2 else "oi"))
    elif cmd == "memoria":
        mems = edith.listar_memoria(20)
        print(json.dumps(mems, indent=2, ensure_ascii=False))
    elif cmd == "lembrete" and len(sys.argv) >= 3:
        print(edith.salvar_lembrete(" ".join(sys.argv[2:])))
    elif cmd == "agenda":
        print(edith._resp_agenda(edith.get_dashboard()))
    elif cmd == "saude":
        print(edith._resp_saude(edith.get_dashboard()))
    elif cmd == "estudos":
        print(edith._resp_estudos(edith.get_dashboard()))
    elif cmd == "produtividade":
        print(edith._resp_prod(edith.get_dashboard()))
    elif cmd == "agendar" and len(sys.argv) >= 4:
        print(edith.acao_add_compromisso(sys.argv[2], sys.argv[3],
                                         sys.argv[4] if len(sys.argv) > 4 else None))
    elif cmd == "tarefa" and len(sys.argv) >= 3:
        print(edith.acao_marcar_tarefa(sys.argv[2]))
    elif cmd == "peso" and len(sys.argv) >= 3:
        print(edith.acao_peso(sys.argv[2]))
    elif cmd == "estudo" and len(sys.argv) >= 3:
        print(edith.acao_estudo(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "geral"))
    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
