from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from typing import List, Optional

# Inicializa a API
app = FastAPI()

# Pega as variáveis de ambiente protegidas da Vercel
DB_URL = os.getenv("DB_JCS")
PASS_ADMIN = os.getenv("PASS_ADMIN")

# ==================== CONEXÃO COM O NEON DB ====================
def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        raise HTTPException(status_code=500, detail="Erro de conexão com o banco de dados")

# ==================== MODELOS DE DADOS (JSON) ====================
class LoginRequest(BaseModel):
    senha: str

class Produto(BaseModel):
    nome: str
    categoria: str
    preco: float
    foto: str
    descricao: str

class Pedido(BaseModel):
    id_pedido: int
    cliente_nome: str
    telefone: str
    endereco: str
    forma_pagamento: str
    itens: str # Resumo em texto dos itens
    total: float
    status: str

class StatusUpdate(BaseModel):
    status: str

# ==================== ROTAS DE SEGURANÇA ====================
@app.post("/api/login")
def validar_login(req: LoginRequest):
    if req.senha == PASS_ADMIN:
        return {"mensagem": "Acesso Autorizado"}
    raise HTTPException(status_code=401, detail="Senha Incorreta")

# ==================== ROTAS DE PRODUTOS (CARDÁPIO) ====================
@app.get("/api/produtos")
def listar_produtos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM produtos ORDER BY categoria, nome;")
    produtos = cursor.fetchall()
    cursor.close()
    conn.close()
    return produtos

@app.post("/api/produtos")
def cadastrar_produto(prod: Produto):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO produtos (nome, categoria, preco, foto, descricao)
        VALUES (%s, %s, %s, %s, %s) RETURNING id;
    """, (prod.nome, prod.categoria, prod.preco, prod.foto, prod.descricao))
    novo_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Produto cadastrado", "id": novo_id}

@app.delete("/api/produtos/{produto_id}")
def excluir_produto(produto_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = %s;", (produto_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Produto excluído com sucesso"}

# ==================== ROTAS DE PEDIDOS (RELATÓRIOS E WHATSAPP) ====================
@app.post("/api/pedidos")
def salvar_pedido(ped: Pedido):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pedidos (id_pedido, cliente_nome, telefone, endereco, forma_pagamento, itens, total, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
    """, (ped.id_pedido, ped.cliente_nome, ped.telefone, ped.endereco, ped.forma_pagamento, ped.itens, ped.total, ped.status))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Pedido salvo no banco com sucesso"}

@app.get("/api/pedidos")
def listar_pedidos():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    # Traz os pedidos ordenados do mais recente para o mais antigo
    cursor.execute("SELECT * FROM pedidos ORDER BY data_criacao DESC;")
    pedidos = cursor.fetchall()
    cursor.close()
    conn.close()
    return pedidos
@app.put("/api/pedidos/{pedido_id}/status")
def atualizar_status_pedido(pedido_id: int, req: StatusUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Atualiza o status do pedido específico no banco Neon
    cursor.execute("UPDATE pedidos SET status = %s WHERE id_pedido = %s;", (req.status, pedido_id))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Status atualizado com sucesso"}
