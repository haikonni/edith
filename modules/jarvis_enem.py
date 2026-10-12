#!/usr/bin/env python3
"""JARVIS - ENEM Study Tracker"""

import argparse
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("EDITH_DATA_DIR", str(Path.home() / "Evolution" / "Jarvis" / "Estudos")))
LOG_FILE = DATA_DIR / "log.jsonl"

MATERIAS = {
    "portugues": {"cor": "📝", "tempo_semana": "10h", "peso": 1.0},
    "redacao": {"cor": "✍️", "tempo_semana": "5h", "peso": 1.2},
    "historia": {"cor": "📜", "tempo_semana": "8h", "peso": 0.9},
    "geografia": {"cor": "🌍", "tempo_semana": "8h", "peso": 0.9},
    "matematica": {"cor": "🔢", "tempo_semana": "12h", "peso": 1.1},
    "fisica": {"cor": "⚡", "tempo_semana": "10h", "peso": 1.0},
    "quimica": {"cor": "🧪", "tempo_semana": "10h", "peso": 1.0},
    "biologia": {"cor": "🧬", "tempo_semana": "8h", "peso": 0.9},
    "filosofia": {"cor": "🤔", "tempo_semana": "4h", "peso": 0.7},
    "sociologia": {"cor": "👥", "tempo_semana": "4h", "peso": 0.7},
}

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def read_log():
    ensure_dirs()
    entries = []
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
    return entries

def write_entry(entry):
    ensure_dirs()
    entry['timestamp'] = datetime.now().isoformat()
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def send_telegram(chat_id, message):
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return False
    import subprocess
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.telegram.org/bot" + os.environ.get("TELEGRAM_BOT_TOKEN", "token") + "/sendMessage",
        "-d", f"chat_id={chat_id}",
        "-d", f"text={message}",
        "-d", "parse_mode=Markdown"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def registrar_estudo(horas: float, materia: str = "geral", chat_id: str = "7174655778"):
    """Registra horas de estudo"""
    write_entry({"tipo": "estudo", "valor": horas, "materia": materia})
    
    # Calcular total da semana
    entries = read_log()
    week_ago = datetime.now().timestamp() - 7 * 86400
    week_studies = [e for e in entries if e['timestamp'] >= datetime.fromtimestamp(week_ago).isoformat() and e['tipo'] == 'estudo']
    total_semana = sum(e['valor'] for e in week_studies)
    
    mat_info = MATERIAS.get(materia, {"cor": "📚", "tempo_semana": "10h", "peso": 1.0})
    
    msg = f"{mat_info['cor']} *Estudo registrado*\n\n"
    msg += f"📖 Matéria: {materia.capitalize()}\n"
    msg += f"⏱️ Horas: {horas}h\n"
    msg += f"📊 Total semanal: {total_semana:.1f}h"
    
    if total_semana >= 35:
        msg += "\n🔥 *Meta semanal atingida!*"
    elif total_semana >= 25:
        msg += "\n💪 *Quase lá!*"
    
    send_telegram(chat_id, msg)
    return msg

def simulado(notas: dict, chat_id: str = "7174655778"):
    """Registra notas de simulado"""
    write_entry({"tipo": "simulado", "notas": notas})
    
    msg = f"📝 *Simulado registrado*\n\n"
    for area, nota in notas.items():
        emoji = "✅" if nota >= 70 else "⚠️" if nota >= 50 else "❌"
        msg += f"{emoji} {area}: {nota}pts\n"
    
    media = sum(notas.values()) / len(notas) if notas else 0
    msg += f"\n📊 Média: {media:.0f}pts"
    
    if media >= 70:
        msg += "\n🔥 *Excelente!*"
    elif media >= 50:
        msg += "\n💪 *Bom, continue!*"
    
    send_telegram(chat_id, msg)
    return msg

def enem_status(chat_id: str = "7174655778"):
    """Status geral dos estudos"""
    entries = read_log()
    now = datetime.now()
    
    # Esta semana
    week_ago = now.timestamp() - 7 * 86400
    week_entries = [e for e in entries if datetime.fromisoformat(e['timestamp']).timestamp() > week_ago and e['tipo'] == 'estudo']
    total_semana = sum(e['valor'] for e in week_entries)
    
    # Por matéria
    por_materia = {}
    for e in week_entries:
        mat = e.get('materia', 'geral')
        por_materia[mat] = por_materia.get(mat, 0) + e['valor']
    
    # Dias restantes
    enem_date = datetime(2027, 1, 16)  # ENEM 2027 - datas prováveis
    dias_restantes = (enem_date - now).days
    
    msg = f"📊 *Status ENEM*\n"
    msg += f"📅 {now.strftime('%d/%m/%Y')}\n"
    msg += f"⏳ {dias_restantes} dias até o ENEM\n\n"
    
    msg += f"📈 *Esta semana:*\n"
    msg += f"⏱️ Total: {total_semana:.1f}h\n"
    
    if total_semana >= 35:
        msg += "🔥 *Meta atingida!* (35h)\n\n"
    elif total_semana >= 25:
        msg += f"💪 *Faltam* {35 - total_semana:.1f}h *(Meta: 35h)*\n\n"
    else:
        msg += f"⚠️ *Abaixo da meta* {35 - total_semana:.1f}h *(Meta: 35h)*\n\n"
    
    msg += "📚 *Por matéria:*\n"
    for mat, horas in sorted(por_materia.items(), key=lambda x: x[1], reverse=True):
        mat_info = MATERIAS.get(mat, {"cor": "📚"})
        msg += f"{mat_info['cor']} {mat.capitalize()}: {horas:.1f}h\n"
    
    if not por_materia:
        msg += "*Nenhum estudo registrado esta semana*\n"
    
    msg += "\n💡 *Dica:* Foque nas matérias com menos horas!"
    
    send_telegram(chat_id, msg)
    return msg

def proxima_revisao(chat_id: str = "7174655778"):
    """Sugere próxima revisão baseada em espaçamento"""
    entries = read_log()
    
    # Materiais estudados recentemente
    studied = set()
    for e in entries:
        if e['tipo'] == 'estudo':
            studied.add(e.get('materia', 'geral'))
    
    # Materiais não estudados esta semana
    week_ago = datetime.now().timestamp() - 7 * 86400
    week_entries = [e for e in entries if datetime.fromisoformat(e['timestamp']).timestamp() > week_ago]
    week_materias = set(e.get('materia', 'geral') for e in week_entries if e['tipo'] == 'estudo')
    
    pendentes = [m for m in MATERIAS if m not in week_materias]
    
    if pendentes:
        # Priorizar por peso (matematica > redacao > etc)
        pendentes.sort(key=lambda m: MATERIAS[m]['peso'], reverse=True)
        proxima = pendentes[0]
        
        msg = f"📚 *Próxima revisão sugerida:*\n\n"
        msg += f"{MATERIAS[proxima]['cor']} {proxima.capitalize()}\n\n"
        msg += f"⏱️ Meta semanal: {MATERIAS[proxima]['tempo_semana']}\n"
        msg += f"🎯 Peso na prova: {MATERIAS[proxima]['peso']}x\n"
        
        # Dicas por matéria
        dicas = {
            "matematica": "Pratique resolução de equações e geometria",
            "portugues": "Releia obras literárias e figuras de linguagem",
            "redacao": "Faça uma redação prática sobre tema atual",
            "historia": "Revise história do Brasil colônia e república",
            "geografia": "Foque em geografia física e brasileira",
            "fisica": "Revise mecânica e eletricidade",
            "quimica": "Foque em química orgânica e soluções",
            "biologia": "Revise ecologia e citologia",
        }
        if proxima in dicas:
            msg += f"\n💡 {dicas[proxima]}"
    else:
        msg = "✅ *Todas as matérias foram estudadas esta semana!*\n\n"
        msg += "🎯 Continue revisando para fixar o conteúdo."
    
    send_telegram(chat_id, msg)
    return msg

def main():
    parser = argparse.ArgumentParser(description="JARVIS ENEM Study Tracker")
    subparsers = parser.add_subparsers(dest='command')
    
    p_estudo = subparsers.add_parser('estudo', help='Registrar estudo')
    p_estudo.add_argument('--horas', type=float, required=True)
    p_estudo.add_argument('--materia', default='geral', choices=list(MATERIAS.keys()) + ['geral'])
    p_estudo.add_argument('--chat', default='7174655778')
    
    p_simulado = subparsers.add_parser('simulado', help='Registrar simulado')
    p_simulado.add_argument('--notas', type=str, required=True, help='Notas por área (ex: humanass=70,natureza=65)')
    p_simulado.add_argument('--chat', default='7174655778')
    
    p_status = subparsers.add_parser('status', help='Status ENEM')
    p_status.add_argument('--chat', default='7174655778')
    
    p_revisao = subparsers.add_parser('revisao', help='Próxima revisão')
    p_revisao.add_argument('--chat', default='7174655778')
    
    args = parser.parse_args()
    
    if args.command == 'estudo':
        print(registrar_estudo(args.horas, args.materia, args.chat))
    elif args.command == 'simulado':
        # Parse notas
        notas = {}
        for pair in args.notas.split(','):
            if '=' in pair:
                k, v = pair.split('=')
                notas[k] = float(v)
        print(simulado(notas, args.chat))
    elif args.command == 'status':
        print(enem_status(args.chat))
    elif args.command == 'revisao':
        print(proxima_revisao(args.chat))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
