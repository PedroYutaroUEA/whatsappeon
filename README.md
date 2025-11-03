# 🔒 Secure Chat (DH + XOR + HMAC)

Chat seguro 1:1 e em grupo (até 5 usuários) com visualização em terminal  
de troca de chaves, cifra e mensagens.

---

## 🧱 Estrutura de pastas

secure-chat/
│
├── server/
│ ├── init.py
│ └── server.py
│
├── client/
│ ├── init.py
│ └── client.py
│
├── requirements.txt
├── README.md
└── .vscode/
└── launch.json

---

## 🚀 Como executar

### 1️⃣ Inicie o servidor
Abra um terminal:
```bash
python server/server.py


Você verá algo como:

[SERVER] rodando em 127.0.0.1:5000
[SERVER] Alice conectado de ('127.0.0.1', 53012)
[SERVER] Alice pubkey = 84293...

2️⃣ Inicie os clientes

Abra até 5 terminais diferentes e rode:

python client/client.py


Cada cliente informará um nome ao iniciar:

Seu nome: Alice
[Alice] conectado ao servidor


3️⃣ Envie mensagens

Digite o nome do destinatário (ex: Bob) ou ALL para enviar a todos:

Destinatário (nome ou ALL p/ grupo): Bob
Mensagem: Olá Bob, tudo seguro?
[Alice] (cifra) -> 4f7a9d32a88f...
[Alice] (msg)   -> Olá Bob, tudo seguro?


No terminal do Bob:

[Bob] (cifra) -> 4f7a9d32a88f...
[Bob] (decifrada) -> Olá Bob, tudo seguro?

4️⃣ Encerrar

Feche o terminal do servidor ou use Ctrl + C para encerrar o chat.

⚙️ Requisitos

Python 3.8+

Nenhuma biblioteca externa (apenas stdlib)

Opcional:

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

🧠 Tecnologias demonstradas

Diffie–Hellman (troca de chaves)

HMAC-SHA256 (integridade/autenticidade)

XOR stream cipher com nonce (confidencialidade)

Comunicação via sockets TCP


---

## ⚙️ `.vscode/launch.json`
Crie o diretório `.vscode` na raiz e salve este arquivo dentro:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "🚀 Rodar Servidor",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/server/server.py",
            "console": "integratedTerminal"
        },
        {
            "name": "💬 Rodar Cliente",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/client/client.py",
            "console": "integratedTerminal"
        }
    ]
}


Com isso, no VS Code você pode:

Escolher “🚀 Rodar Servidor” e pressionar F5 para iniciar o servidor.

Abrir novos terminais e escolher “💬 Rodar Cliente” para iniciar clientes.