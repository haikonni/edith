#!/usr/bin/env python3
"""JARVIS - Productivity & Daily Checklist"""

import argparse
import os
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("EDITH_DATA_DIR", str(Path.home() / "Evolution"))) / "Jarvis" / "Produtividade"
LOG_FILE = DATA_DIR / "log.jsonl"
TASKS_FILE = DATA_DIR / "tarefas.json"

TAREFAS_PADRAO = [
    {"id": 1, "texto": "Acordar 06:30", "feito": False},
    {"id": 2, "texto": "Exercício matinal", "feito": False},
    {"id": 3, "texto": "Café da manhã saudável", "feito": False},
    {"id": 4, "texto": "Estudar 2h antes do colégio", "feito": False},
    {"id": 5, "texto": "Colégio 19:00-22:20", "feito": False},
    {"id": 6, "texto": "Jantar em casa", "feito": False},
    {"id": 7, "texto": "Estudar 2h pós-colégio", "feito": False},
    {"id": 8, "texto": "Preparar material do dia seguinte", "feito": False},
    {"id": 9, "texto": "Dormir 23:30", "feito": False},
]

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

def load_tarefas():
    ensure_dirs()
    if TASKS_FILE.exists():
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    return {"tarefas": TAREFAS_PADRAO, "data": datetime.now().strftime("%Y-%m-%d")}

def save_tarefas(tarefas):
    ensure_dirs()
    with open(TASKS_FILE, 'w') as f:
        json.dump(tarefas, f, indent=2, ensure_ascii=False)

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

def checklist_diario(chat_id: str = "7174655778"):
    """Checklist diário completo"""
    tarefas = load_tarefas()
    
    # Resetar se for novo dia
    hoje = datetime.now().strftime("%Y-%m-%d")
    if tarefas.get('data') != hoje:
        tarefas = {"tarefas": [t for t in TAREFAS_PADRAO], "data": hoje}
        save_tarefas(tarefas)
    
    msg = f"✅ *Checklist Diário*\n📅 {hoje}\n\n"
    
    concluidas = sum(1 for t in tarefas['tarefas'] if t.get('feito', False))
    total = len(tarefas['tarefas'])
    
    for t in tarefas['tarefas']:
        status = "✅" if t.get('feito', False) else "⬜"
        msg += f"{status} {t['texto']}\n"
    
    msg += f"\n📊 Progresso: {concluidas}/{total}"
    
    if concluidas == total:
        msg += "\n🔥 *TUDO CONCLUÍDO!*"
    elif concluidas >= total * 0.7:
        msg += "\n💪 *Bom progresso!*"
    else:
        msg += "\n⚠️ *Falta pouco!*"
    
    send_telegram(chat_id, msg)
    return msg

def marcar_tarefa(id_tarefa: int, chat_id: str = "7174655778"):
    """Marca tarefa como feita"""
    tarefas = load_tarefas()
    
    for t in tarefas['tarefas']:
        if t['id'] == id_tarefa:
            t['feito'] = not t.get('feito', False)
            break
    
    save_tarefas(tarefas)
    
    tarefa = next((t for t in tarefas['tarefas'] if t['id'] == id_tarefa), None)
    status = "✅ Feito" if tarefa.get('feito') else "⬜ Desfeito"
    
    msg = f"{status}: {tarefa['texto']}\n"
    
    concluidas = sum(1 for t in tarefas['tarefas'] if t.get('feito', False))
    msg += f"📊 Progresso: {concluidas}/{len(tarefas['tarefas'])}"
    
    send_telegram(chat_id, msg)
    return msg

def review_semanal(chat_id: str = "7174655778"):
    """Review semanal de produtividade"""
    entries = read_log()
    
    # Análise dos últimos 7 dias
    week_ago = datetime.now().timestamp() - 7 * 86400
    week_entries = [e for e in entries if datetime.fromisoformat(e['timestamp']).timestamp() > week_ago]
    
    estudos = [e for e in week_entries if e['tipo'] == 'estudo']
    pesoses = [e for e in week_entries if e['tipo'] == 'peso']
    treinos = [e for e in week_entries if e['tipo'] == 'treino']
    sonos = [e for e in week_entries if e['tipo'] == 'sono']
    
    total_estudos = sum(e['valor'] for e in estudos)
    avg_sono = sum(e['valor'] for e in sonos) / len(sonos) if sonos else 0
    
    msg = f"📊 *Review Semanal*\n📅 {datetime.now().strftime('%d/%m')}\n\n"
    
    msg += f"📚 Estudos: {total_estudos:.1f}h (meta: 35h)\n"
    msg += f"🏋️ Treinos: {len(treinos)}\n"
    msg += f"⚖️ Peso início: {pesoses[0]['valor'] if pesoses else '?'}kg\n"
    msg += f"⚖️ Peso fim: {pesoses[-1]['valor'] if pesoses else '?'}kg\n"
    msg += f"😴 Sono médio: {avg_sono:.1f}h\n\n"
    
    # Score geral
    score = 0
    if total_estudos >= 35: score += 25
    elif total_estudos >= 25: score += 15
    if len(treinos) >= 10: score += 25
    elif len(treinos) >= 7: score += 15
    if avg_sono >= 7: score += 25
    elif avg_sono >= 6: score += 15
    if pesoses and pesoses[-1]['valor'] <= pesoses[0]['valor']: score += 25
    elif pesoses: score += 10
    
    msg += f"🎯 *Score semanal: {score}/100*"
    
    if score >= 80:
        msg += "\n🔥 *Excelente semana!*"
    elif score >= 60:
        msg += "\n💪 *Boa semana!*"
    else:
        msg += "\n⚠️ *Semana para melhorar*"
    
    send_telegram(chat_id, msg)
    return msg

def metas_proximo(chat_id: str = "7174655778"):
    """Metas próximas"""
    now = datetime.now()
    
    # Metas do usuário (configuráveis)
    metas = {
        "peso": {"atual": 75.2, "meta": 70, "unidade": "kg"},
        "estudos_semanais": {"atual": 25, "meta": 35, "unidade": "h"},
        "treinos_semanais": {"atual": 10, "meta": 12, "unidade": ""},
        "sono_medio": {"atual": 6.5, "meta": 7.5, "unidade": "h"},
    }
    
    msg = f"🎯 *Metas Próximas*\n📅 {now.strftime('%d/%m/%Y')}\n\n"
    
    # Peso
    peso = metas['peso']
    delta = peso['atual'] - peso['meta']
    if delta > 0:
        msg += f"⚖️ Peso: {peso['atual']}kg → {peso['meta']}kg ({delta:.1f}kg a perder)\n"
    else:
        msg += f"⚖️ Peso: {peso['atual']}kg (meta atingida!)\n"
    
    # Estudos
    est = metas['estudos_semanais']
    faltam = est['meta'] - est['atual']
    if faltam > 0:
        msg += f"📚 Estudos: {est['atual']}h/{est['meta']}h ({faltam}h faltam)\n"
    else:
        msg += f"📚 Estudos: {est['atual']}h (meta atingida!)\n"
    
    # Treinos
    tre = metas['treinos_semanais']
    faltam = tre['meta'] - tre['atual']
    msg += f"🏋️ Treinos: {tre['atual']}/{tre['meta']}\n"
    
    # Sono
    sono = metas['sono_medio']
    if sono['atual'] < sono['meta']:
        msg += f"😴 Sono: {sono['atual']}h → {sono['meta']}h\n"
    else:
        msg += f"😴 Sono: {sono['atual']}h ✅\n"
    
    msg += "\n💡 *Dica:* Foque em uma meta por vez!"
    
    send_telegram(chat_id, msg)
    return msg

def main():
    parser = argparse.ArgumentParser(description="JARVIS Productivity Tracker")
    subparsers = parser.add_subparsers(dest='command')
    
    p_check = subparsers.add_parser('checklist', help='Checklist diário')
    p_check.add_argument('--chat', default='7174655778')
    
    p_marcar = subparsers.add_parser('marcar', help='Marcar tarefa')
    p_marcar.add_argument('--id', type=int, required=True, help='ID da tarefa')
    p_marcar.add_argument('--chat', default='7174655778')
    
    p_review = subparsers.add_parser('review', help='Review semanal')
    p_review.add_argument('--chat', default='7174655778')
    
    p_metas = subparsers.add_parser('metas', help='Metas próximas')
    p_metas.add_argument('--chat', default='7174655778')
    
    args = parser.parse_args()
    
    if args.command == 'checklist':
        print(checklist_diario(args.chat))
    elif args.command == 'marcar':
        print(marcar_tarefa(args.id, args.chat))
    elif args.command == 'review':
        print(review_semanal(args.chat))
    elif args.command == 'metas':
        print(metas_proximo(args.chat))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
