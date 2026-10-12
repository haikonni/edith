#!/usr/bin/env python3
"""Edith Web Server - Flask API (v1 versionada + health check)."""
import os
import uuid
from flask import Flask, render_template, jsonify, request
from edith import Edith

app = Flask(__name__, template_folder='templates')
edith = Edith()


def err(code: str, message: str, status: int, details=None):
    return jsonify({"code": code, "message": message,
                    "details": details or [], "request_id": uuid.uuid4().hex[:8]}), status


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok", "service": "edith"})


# --- v1 (contrato atual; rotas antigas mantidas como alias) ---
@app.route('/v1/dashboard')
@app.route('/api/dashboard')
def api_dashboard():
    return jsonify(edith.get_dashboard())


@app.route('/v1/chat', methods=['POST'])
@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message:
        return err("VALIDATION_ERROR", "Campo 'message' é obrigatório.", 422,
                   [{"field": "message", "issue": "vazio ou ausente"}])
    return jsonify({'response': edith.chat(message)})


@app.route('/v1/agenda', methods=['GET', 'POST'])
@app.route('/api/agenda', methods=['GET', 'POST'])
def api_agenda():
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        titulo = (data.get('titulo') or '').strip()
        data_ev = (data.get('data') or '').strip()
        if not titulo or not data_ev:
            return err("VALIDATION_ERROR", "Campos 'titulo' e 'data' (AAAA-MM-DD) são obrigatórios.", 422)
        return jsonify({'result': edith.acao_add_compromisso(
            titulo, data_ev, data.get('hora'), data.get('categoria', 'geral'), data.get('nota'))}), 201
    dash = edith.get_dashboard()['agenda']
    return jsonify(dash)


@app.route('/v1/tarefas/<int:tid>/concluir', methods=['POST'])
def api_tarefa_concluir(tid):
    return jsonify({'result': edith.acao_marcar_tarefa(tid)})


@app.route('/v1/saude/peso', methods=['POST'])
def api_peso():
    data = request.get_json(silent=True) or {}
    if 'kg' not in data:
        return err("VALIDATION_ERROR", "Campo 'kg' é obrigatório.", 422)
    try:
        return jsonify({'result': edith.acao_peso(float(data['kg']))}), 201
    except (ValueError, TypeError):
        return err("VALIDATION_ERROR", "Campo 'kg' deve ser numérico.", 422)


@app.route('/v1/saude/treino', methods=['POST'])
def api_treino():
    data = request.get_json(silent=True) or {}
    if not data.get('tipo'):
        return err("VALIDATION_ERROR", "Campo 'tipo' é obrigatório.", 422)
    try:
        dur = int(data.get('duracao', 60))
    except (ValueError, TypeError):
        return err("VALIDATION_ERROR", "Campo 'duracao' deve ser inteiro (min).", 422)
    return jsonify({'result': edith.acao_treino(data['tipo'], dur)}), 201


@app.route('/v1/estudos', methods=['POST'])
def api_estudo():
    data = request.get_json(silent=True) or {}
    if 'horas' not in data:
        return err("VALIDATION_ERROR", "Campo 'horas' é obrigatório.", 422)
    try:
        horas = float(data['horas'])
    except (ValueError, TypeError):
        return err("VALIDATION_ERROR", "Campo 'horas' deve ser numérico.", 422)
    return jsonify({'result': edith.acao_estudo(horas, data.get('materia', 'geral'))}), 201


# Aliases antigos (GET leitura)
@app.route('/api/saude')
def api_saude():
    return jsonify(edith.get_dashboard()['saude'])


@app.route('/api/estudos')
def api_estudos():
    return jsonify(edith.get_dashboard()['estudos'])


@app.route('/api/produtividade')
def api_produtividade():
    return jsonify(edith.get_dashboard()['produtividade'])


@app.errorhandler(404)
def nf(_e):
    return err("NOT_FOUND", "Rota não encontrada. Use /v1/*.", 404)


@app.errorhandler(500)
def ie(_e):
    return err("INTERNAL_ERROR", "Erro interno. Tente de novo.", 500)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Edith iniciada em http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
