#!/usr/bin/env python3
"""JARVIS - Agenda Manager"""

import argparse
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(os.environ.get("EDITH_DATA_DIR", str(Path.home() / "Evolution" / "Jarvis" / "Agenda")))
LOG_FILE = DATA_DIR / "compromissos.jsonl"
CALENDAR_FILE = DATA_DIR / "calendario.json"

def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def read_compromissos():
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

def write_compromisso(compromisso):
    ensure_dirs()
    compromisso['criado_em'] = datetime.now().isoformat()
    compromisso['id'] = len(read_compromissos()) + 1
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(compromisso, ensure_ascii=False) + '\n')
    return compromisso['id']

def read_calendar():
    ensure_dirs()
    if CALENDAR_FILE.exists():
        with open(CALENDAR_FILE, 'r') as f:
            return json.load(f)
    return {"eventos": [], "notas": {}}

def save_calendar(calendar):
    ensure_dirs()
    with open(CALENDAR_FILE, 'w') as f:
        json.dump(calendar, f, indent=2, ensure_ascii=False)

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

def add_compromisso(titulo: str, data: str, hora: str = None, nota: str = None, categoria: str = "geral", chat_id: str = "7174655778"):
    """Adiciona compromisso"""
    # Validar data
    try:
        data_obj = datetime.strptime(data, "%Y-%m-%d")
    except:
        return "❌ Data inválida. Use YYYY-MM-DD"
    
    compromisso = {
        "titulo": titulo,
        "data": data,
        "hora": hora,
        "nota": nota,
        "categoria": categoria,
        "feito": False,
    }
    
    cid = write_compromisso(compromisso)
    
    # Emoji por categoria
    emojis = {
        "trabalho": "💼",
        "estudos": "📚",
        "saude": "💪",
        "pessoal": "🏠",
        "social": "👥",
        "geral": "📌",
    }
    emoji = emojis.get(categoria, "📌")
    
    msg = f"{emoji} *Compromisso adicionado*\n\n"
    msg += f"📋 #{cid}: {titulo}\n"
    msg += f"📅 {data_obj.strftime('%d/%m/%Y')}"
    if hora:
        msg += f" às {hora}"
    msg += f"\n📁 Categoria: {categoria.capitalize()}\n"
    
    if nota:
        msg += f"💡 {nota}\n"
    
    # Verificar quantos compromissos no mesmo dia
    todos = read_compromissos()
    mesmo_dia = [c for c in todos if c['data'] == data and not c.get('feito')]
    msg += f"\n📊 Total no dia: {len(mesmo_dia)} compromissos"
    
    send_telegram(chat_id, msg)
    return msg

def listar_compromissos(data: str = None, chat_id: str = "7174655778"):
    """Lista compromissos"""
    todos = read_compromissos()
    hoje = datetime.now().strftime("%Y-%m-%d")
    
    if data:
        compromissos = [c for c in todos if c['data'] == data]
    else:
        # Próximos 7 dias
        hoje_dt = datetime.now()
        semana_dt = hoje_dt + timedelta(days=7)
        compromissos = [
            c for c in todos 
            if not c.get('feito') 
            and hoje_dt <= datetime.strptime(c['data'], "%Y-%m-%d") <= semana_dt
        ]
    
    if not compromissos:
        msg = "📭 *Nenhum compromisso próximo*"
        send_telegram(chat_id, msg)
        return msg
    
    msg = f"📅 *Compromissos*"
    if data:
        msg += f" - {datetime.strptime(data, '%Y-%m-%d').strftime('%d/%m/%Y')}"
    msg += f"\n\n"
    
    # Agrupar por data
    by_date = {}
    for c in compromissos:
        d = c['data']
        if d not in by_date:
            by_date[d] = []
        by_date[d].append(c)
    
    for data, comps in sorted(by_date.items()):
        date_obj = datetime.strptime(data, "%Y-%m-%d")
        msg += f"**{date_obj.strftime('%d/%m/%Y')}** ({date_obj.strftime('%a')})\n"
        
        for c in comps:
            emoji = "✅" if c.get('feito') else "⬜"
            hora = f" {c['hora']}" if c.get('hora') else ""
            msg += f"{emoji} {c['hora'] or ''} {c['titulo']}\n"
        
        msg += "\n"
    
    send_telegram(chat_id, msg)
    return msg

def marcar_feito(id_compromisso: int, chat_id: str = "7174655778"):
    """Marca compromisso como feito"""
    todos = read_compromissos()
    
    for i, c in enumerate(todos):
        if c['id'] == id_compromisso:
            c['feito'] = not c.get('feito', False)
            break
    else:
        return f"❌ Compromisso #{id_compromisso} não encontrado"
    
    # Salvar de volta (sobrescreve arquivo)
    with open(LOG_FILE, 'w') as f:
        for c in todos:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')
    
    status = "✅ Feito" if c['feito'] else "⬜ Desfeito"
    msg = f"{status}: #{id_compromisso} - {c['titulo']}\n"
    
    # Contagem
    pendentes = sum(1 for c in todos if not c.get('feito'))
    msg += f"📊 Pendentes: {pendentes}"
    
    if pendentes == 0:
        msg += "\n🔥 *Tudo em dia!*"
    
    send_telegram(chat_id, msg)
    return msg

def verificar_agenda(horas_alerta: int = 2, chat_id: str = "7174655778"):
    """Verifica compromissos próximos"""
    todos = read_compromissos()
    agora = datetime.now()
    alerta_horas = timedelta(hours=horas_alerta)
    
    proximos = []
    for c in todos:
        if c.get('feito'):
            continue
        data_comp = datetime.strptime(c['data'], "%Y-%m-%d")
        if c.get('hora'):
            try:
                hora_comp = datetime.strptime(c['hora'], "%H:%M")
                data_comp = data_comp.replace(hour=hora_comp.hour, minute=hora_comp.minute)
            except:
                pass
        
        diferenca = data_comp - agora
        if timedelta(0) < diferenca <= alerta_horas:
            proximos.append((c, diferenca))
    
    if not proximos:
        msg = "✅ *Nenhum compromisso nas próximas " + str(horas_alerta) + "h*"
        send_telegram(chat_id, msg)
        return msg
    
    msg = f"⏰ *Lembretes - Próximas {horas_alerta}h*\n\n"
    
    for c, diff in sorted(proximos, key=lambda x: x[1]):
        horas_faltam = diff.total_seconds() / 3600
        if horas_faltam < 1:
            mins = diff.total_seconds() / 60
            msg += f"🔔 *EM BREVE*: {c['titulo']} ({mins:.0f}min)\n"
        else:
            msg += f"🔔 *Em {horas_faltam:.1f}h*: {c['titulo']}\n"
        
        if c.get('nota'):
            msg += f"   💡 {c['nota']}\n"
    
    msg += "\n⏰ *Não esqueça!*"
    
    send_telegram(chat_id, msg)
    return msg

def adicionar_evento(dia: int, mes: int, ano: int, titulo: str, cor: str = None, chat_id: str = "7174655778"):
    """Adiciona evento ao calendário visual"""
    calendar = read_calendar()
    
    data_str = f"{ano}-{mes:02d}-{dia:02d}"
    
    evento = {
        "titulo": titulo,
        "data": data_str,
        "cor": cor or "🟢",
    }
    
    calendar["eventos"].append(evento)
    save_calendar(calendar)
    
    msg = f"📅 *Evento adicionado ao calendário*\n\n"
    msg += f"🗓️ {dia:02d}/{mes:02d}/{ano}\n"
    msg += f"📌 {titulo}\n"
    
    send_telegram(chat_id, msg)
    return msg

def ver_calendario(ano: int = None, mes: int = None, chat_id: str = "7174655778"):
    """Ver calendário mensal"""
    calendar = read_calendar()
    now = datetime.now()
    
    ano = ano or now.year
    mes = mes or now.month
    
    # Dias do mês
    import calendar as cal
    dias_no_mes = cal.monthrange(ano, mes)[1]
    primeiro_dia = cal.monthrange(ano, mes)[0]  # 0=segunda
    
    msg = f"📅 *Calendário - {mes:02d}/{ano}*\n\n"
    msg += "Seg Ter Qua Qui Sex Sab Dom\n"
    
    # Preencher primeira linha
    linha = " " * (primeiro_dia * 4)
    
    for dia in range(1, dias_no_mes + 1):
        data_str = f"{ano}-{mes:02d}-{dia:02d}"
        eventos_dia = [e for e in calendar["eventos"] if e["data"] == data_str]
        
        dia_str = f"{dia:2d}"
        if eventos_dia:
            dias_no_str = len(eventos_dia)
            dia_str = f"{dia:2d}•{dias_no_str}"
        
        if dia == now.day and mes == now.month and ano == now.year:
            dia_str = f"[{dia:2d}]"
        
        linha += dia_str + " "
        
        if (primeiro_dia + dia) % 7 == 0:
            msg += linha.rstrip() + "\n"
            linha = ""
    
    if linha.strip():
        msg += linha.rstrip() + "\n"
    
    # Eventos do mês
    eventos_mes = [e for e in calendar["eventos"] if e["data"].startswith(f"{ano}-{mes:02d}")]
    if eventos_mes:
        msg += "\n*Eventos do mês:*\n"
        for e in sorted(eventos_mes, key=lambda x: x["data"]):
            dia = datetime.strptime(e["data"], "%Y-%m-%d").day
            msg += f"📌 Dia {dia}: {e['titulo']}\n"
    
    send_telegram(chat_id, msg)
    return msg

def adicionar_nota(data: str, nota: str, titulo: str = None, chat_id: str = "7174655778"):
    """Adiciona nota ao calendário"""
    calendar = read_calendar()
    
    if "notas" not in calendar:
        calendar["notas"] = {}
    
    if data not in calendar["notas"]:
        calendar["notas"][data] = []
    
    entrada = {
        "titulo": titulo,
        "texto": nota,
        "criado_em": datetime.now().isoformat(),
    }
    
    calendar["notas"][data].append(entrada)
    save_calendar(calendar)
    
    msg = f"📝 *Nota adicionada*\n\n"
    msg += f"📅 {data}\n"
    if titulo:
        msg += f"📌 {titulo}\n"
    msg += f"💬 {nota}"
    
    send_telegram(chat_id, msg)
    return msg

def ver_notas(data: str = None, chat_id: str = "7174655778"):
    """Lista notas"""
    calendar = read_calendar()
    notas = calendar.get("notas", {})
    
    if data:
        notas_dia = notas.get(data, [])
    else:
        # Notas dos últimos 7 dias
        hoje = datetime.now()
        notas_dia = []
        for i in range(7):
            d = (hoje - timedelta(days=i)).strftime("%Y-%m-%d")
            notas_dia.extend(notas.get(d, []))
    
    if not notas_dia:
        msg = "📭 *Nenhuma nota encontrada*"
        send_telegram(chat_id, msg)
        return msg
    
    msg = f"📝 *Notas*"
    if data:
        msg += f" - {data}"
    msg += "\n\n"
    
    for n in notas_dia:
        msg += f"📌 {n.get('titulo', 'Sem título')}:\n"
        msg += f"   {n['texto']}\n\n"
    
    send_telegram(chat_id, msg)
    return msg

def main():
    parser = argparse.ArgumentParser(description="JARVIS Agenda Manager")
    subparsers = parser.add_subparsers(dest='command')
    
    # add
    p_add = subparsers.add_parser('add', help='Adicionar compromisso')
    p_add.add_argument('--titulo', required=True, help='Título')
    p_add.add_argument('--data', required=True, help='Data (YYYY-MM-DD)')
    p_add.add_argument('--hora', default=None, help='Hora (HH:MM)')
    p_add.add_argument('--nota', default=None, help='Nota opcional')
    p_add.add_argument('--categoria', default='geral', choices=['trabalho', 'estudos', 'saude', 'pessoal', 'social', 'geral'])
    p_add.add_argument('--chat', default='7174655778')
    
    # list
    p_list = subparsers.add_parser('list', help='Listar compromissos')
    p_list.add_argument('--data', default=None, help='Filtrar por data (YYYY-MM-DD)')
    p_list.add_argument('--chat', default='7174655778')
    
    # done
    p_done = subparsers.add_parser('done', help='Marcar como feito')
    p_done.add_argument('--id', type=int, required=True, help='ID do compromisso')
    p_done.add_argument('--chat', default='7174655778')
    
    # check
    p_check = subparsers.add_parser('check', help='Verificar compromissos próximos')
    p_check.add_argument('--alerta', type=int, default=2, help='Horas de alerta')
    p_check.add_argument('--chat', default='7174655778')
    
    # calendar
    p_cal = subparsers.add_parser('calendar', help='Ver calendário')
    p_cal.add_argument('--ano', type=int, default=None)
    p_cal.add_argument('--mes', type=int, default=None)
    p_cal.add_argument('--chat', default='7174655778')
    
    # event
    p_event = subparsers.add_parser('event', help='Adicionar evento ao calendário')
    p_event.add_argument('--dia', type=int, required=True)
    p_event.add_argument('--mes', type=int, required=True)
    p_event.add_argument('--ano', type=int, required=True)
    p_event.add_argument('--titulo', required=True)
    p_event.add_argument('--cor', default=None)
    p_event.add_argument('--chat', default='7174655778')
    
    # note
    p_note = subparsers.add_parser('note', help='Adicionar nota')
    p_note.add_argument('--data', required=True, help='Data (YYYY-MM-DD)')
    p_note.add_argument('--nota', required=True, help='Nota')
    p_note.add_argument('--titulo', default=None)
    p_note.add_argument('--chat', default='7174655778')
    
    # notes
    p_notes = subparsers.add_parser('notes', help='Ver notas')
    p_notes.add_argument('--data', default=None)
    p_notes.add_argument('--chat', default='7174655778')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        print(add_compromisso(args.titulo, args.data, args.hora, args.nota, args.categoria, args.chat))
    elif args.command == 'list':
        print(listar_compromissos(args.data, args.chat))
    elif args.command == 'done':
        print(marcar_feito(args.id, args.chat))
    elif args.command == 'check':
        print(verificar_agenda(args.alerta, args.chat))
    elif args.command == 'calendar':
        print(ver_calendario(args.ano, args.mes, args.chat))
    elif args.command == 'event':
        print(adicionar_evento(args.dia, args.mes, args.ano, args.titulo, args.cor, args.chat))
    elif args.command == 'note':
        print(adicionar_nota(args.data, args.nota, args.titulo, args.chat))
    elif args.command == 'notes':
        print(ver_notas(args.data, args.chat))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
