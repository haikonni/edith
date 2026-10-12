#!/usr/bin/env python3
"""JARVIS - Health & Fitness Tracker"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("EDITH_DATA_DIR", str(Path.home() / "Evolution"))) / "Jarvis" / "Saude"
LOG_FILE = DATA_DIR / "log.jsonl"

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
    import subprocess
    cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.telegram.org/bot[REDACTED]/sendMessage",
        "-d", f"chat_id={chat_id}",
        "-d", f"text={message}",
        "-d", "parse_mode=Markdown"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except:
        return False

def registrar_peso(kg: float, chat_id: str = "7174655778"):
    write_entry({"tipo": "peso", "valor": kg})
    entries = read_log()
    recent = [e for e in entries if e['tipo'] == 'peso' and 
              (datetime.now() - datetime.fromisoformat(e['timestamp'])).days <= 7]
    
    if len(recent) >= 2:
        first = recent[-1]['valor']
        last = kg
        delta = last - first
        arrow = "📉" if delta < 0 else "📈" if delta > 0 else "➡️"
        msg = f"⚖️ *Peso registrado*\n\n{arrow} {last}kg ({delta:+.1f}kg vs {first}kg)"
    else:
        msg = f"⚖️ *Peso registrado*: {kg}kg"
    
    send_telegram(chat_id, msg)
    return msg

def registrar_treino(tipo: str, duracao: int, chat_id: str = "7174655778"):
    write_entry({"tipo": "treino", "valor": tipo, "duracao": duracao})
    msg = f"🏋️ *Treino registrado*\n\n📌 {tipo}\n⏱️ {duracao}min"
    send_telegram(chat_id, msg)
    return msg

def registrar_sono(horas: float, chat_id: str = "7174655778"):
    write_entry({"tipo": "sono", "valor": horas})
    quality = "✅ Bom" if horas >= 7 else "⚠️ Pouco" if horas < 6 else "👍 Ok"
    msg = f"😴 *Sono registrado*\n\n{quality}: {horas}h"
    send_telegram(chat_id, msg)
    return msg

def registrar_comida(descricao: str, kcal: int = None, proteinas: float = None, chat_id: str = "7174655778"):
    write_entry({"tipo": "comida", "valor": descricao, "kcal": kcal, "proteinas": proteinas})
    msg = f"🍽️ *Refeição registrada*\n\n📝 {descricao}"
    if kcal:
        msg += f"\n🔥 {kcal}kcal"
    if proteinas:
        msg += f"\n🥩 {proteinas}g proteína"
    send_telegram(chat_id, msg)
    return msg

def saude_check(chat_id: str = "7174655778"):
    """Check diário de saúde"""
    today = datetime.now().strftime("%Y-%m-%d")
    entries = read_log()
    today_entries = [e for e in entries if e['timestamp'].startswith(today)]
    
    msg = f"💪 *Check Diário de Saúde*\n📅 {today}\n\n"
    
    pesos = [e for e in today_entries if e['tipo'] == 'peso']
    treinos = [e for e in today_entries if e['tipo'] == 'treino']
    sonos = [e for e in today_entries if e['tipo'] == 'sono']
    comidas = [e for e in today_entries if e['tipo'] == 'comida']
    
    if pesos:
        msg += f"⚖️ Peso: {pesos[-1]['valor']}kg\n"
    else:
        msg += "⚖️ Peso: *não registrado*\n"
    
    if treinos:
        for t in treinos:
            msg += f"🏋️ Treino: {t['valor']} ({t.get('duracao', '?')}min)\n"
    else:
        msg += "🏋️ Treino: *não registrado*\n"
    
    if sonos:
        msg += f"😴 Sono: {sonos[-1]['valor']}h\n"
    else:
        msg += "😴 Sono: *não registrado*\n"
    
    if comidas:
        msg += f"🍽️ Refeições: {len(comidas)}\n"
    else:
        msg += "🍽️ Refeições: *não registradas*\n"
    
    msg += "\n*Lembrete:* Registre seus dados acima!"
    
    send_telegram(chat_id, msg)
    return msg

def progresso_semanal(chat_id: str = "7174655778"):
    """Análise semanal de saúde"""
    entries = read_log()
    week_ago = datetime.now().timestamp() - 7 * 86400
    
    recent = [e for e in entries if datetime.fromisoformat(e['timestamp']).timestamp() > week_ago]
    
    pesos = [e for e in recent if e['tipo'] == 'peso']
    treinos = [e for e in recent if e['tipo'] == 'treino']
    sonos = [e for e in recent if e['tipo'] == 'sono']
    
    msg = f"📊 *Progresso Semanal*\n\n"
    
    if len(pesos) >= 2:
        first = pesos[0]['valor']
        last = pesos[-1]['valor']
        delta = last - first
        arrow = "📉" if delta < 0 else "📈"
        msg += f"⚖️ Peso: {first}kg → {last}kg ({delta:+.1f}kg)\n"
    
    msg += f"🏋️ Treinos: {len(treinos)}\n"
    
    if sonos:
        avg_sono = sum(s['valor'] for s in sonos) / len(sonos)
        msg += f"😴 Sono médio: {avg_sono:.1f}h\n"
    
    msg += "\n*Continue firme! 💪*"
    
    send_telegram(chat_id, msg)
    return msg

def main():
    parser = argparse.ArgumentParser(description="JARVIS Health Tracker")
    subparsers = parser.add_subparsers(dest='command')
    
    # peso
    p_peso = subparsers.add_parser('peso', help='Registrar peso')
    p_peso.add_argument('--kg', type=float, required=True, help='Peso em kg')
    p_peso.add_argument('--chat', default='7174655778')
    
    # treino
    p_treino = subparsers.add_parser('treino', help='Registrar treino')
    p_treino.add_argument('--tipo', required=True, help='Tipo de treino')
    p_treino.add_argument('--duracao', type=int, default=60, help='Duração em minutos')
    p_treino.add_argument('--chat', default='7174655778')
    
    # sono
    p_sono = subparsers.add_parser('sono', help='Registrar sono')
    p_sono.add_argument('--horas', type=float, required=True, help='Horas de sono')
    p_sono.add_argument('--chat', default='7174655778')
    
    # comida
    p_comida = subparsers.add_parser('comida', help='Registrar refeição')
    p_comida.add_argument('--descricao', required=True, help='Descrição da refeição')
    p_comida.add_argument('--kcal', type=int, help='Calorias')
    p_comida.add_argument('--proteinas', type=float, help='Proteínas em g')
    p_comida.add_argument('--chat', default='7174655778')
    
    # check
    p_check = subparsers.add_parser('check', help='Check diário')
    p_check.add_argument('--chat', default='7174655778')
    
    # semanal
    p_semanal = subparsers.add_parser('semanal', help='Progresso semanal')
    p_semanal.add_argument('--chat', default='7174655778')
    
    args = parser.parse_args()
    
    if args.command == 'peso':
        print(registrar_peso(args.kg, args.chat))
    elif args.command == 'treino':
        print(registrar_treino(args.tipo, args.duracao, args.chat))
    elif args.command == 'sono':
        print(registrar_sono(args.horas, args.chat))
    elif args.command == 'comida':
        print(registrar_comida(args.descricao, args.kcal, args.proteinas, args.chat))
    elif args.command == 'check':
        print(saude_check(args.chat))
    elif args.command == 'semanal':
        print(progresso_semanal(args.chat))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
