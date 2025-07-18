# Sistema de Inventário Otimizado 📦📊

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-2.3-lightgrey)
![MIT License](https://img.shields.io/badge/license-MIT-green)

Sistema web robusto para **gerenciamento de inventário**, desenvolvido com **Flask** no backend e **HTML/CSS/JavaScript (Bootstrap 5)** no frontend. Permite contagem de estoque, auditoria, recontagem, geração de relatórios e consulta por chatbot com inteligência artificial (Gemini AI), com diferentes perfis de usuário (Gestor e Contador).

---

## 📚 Índice

- [🚀 Funcionalidades Principais](#-funcionalidades-principais)
- [🛠️ Tecnologias Utilizadas](#️-tecnologias-utilizadas)
- [⚙️ Configuração e Execução](#️-configuração-e-execução)
- [📂 Estrutura do Projeto](#-estrutura-do-projeto)
- [⚠️ Considerações de Segurança](#️-considerações-de-segurança)
- [🤝 Contribuições](#-contribuições)
- [📄 Licença](#-licença)

---

## 🚀 Funcionalidades Principais

### 🔐 Autenticação de Usuários
- Login e cadastro com perfis `gestor` ou `contador`.

### 📊 Painel do Gestor
- Visão geral por status: pendente, em andamento, concluído, verificado.
- Filtro e visualização de itens.
- Análise de divergência por percentual.
- Auditoria e recontagem em lote.
- Geração de relatórios Excel.
- Upload de nova base via planilha.
- Redefinição de senhas.
- Integração com Chatbot (Gemini AI).

### 📦 Painel do Contador
- Execução de contagem e recontagem.
- Escolha da ordem de contagem (Balcão ou Depósito).
- Contagem item a item com salvamento automático.
- Adição de novos lotes/produtos.
- Busca de produtos.

### 🗃️ Gerenciamento de Dados
- Banco de dados **SQLite** (`inventario.db`).
- Pool de conexões (`ConnectionPool`).
- Sistema de cache para dados frequentes.

### ⚡ Performance e UX
- **AJAX** para carregamento dinâmico.
- **Bootstrap 5** para layout responsivo.
- Carregamento otimizado com `preconnect` e `defer`.
- **Service Workers** para modo offline (PWA).
- Monitoramento com `web-vitals`.

---

## 🛠️ Tecnologias Utilizadas

### Backend
- Python 3.x
- Flask
- Werkzeug
- Pandas
- Openpyxl
- Waitress
- python-dotenv
- sqlite3
- aiofiles
- Google-GenerativeAI (Gemini)

### Frontend
- HTML5 + CSS3
- Bootstrap 5
- Font Awesome 6
- JavaScript
- jQuery
- DataTables
- Web Vitals

---

## ⚙️ Configuração e Execução

### ✅ Pré-requisitos
- Python 3.x instalado.
- `pip` (gerenciador de pacotes).

### 1. Clonar o Repositório

```bash
git clone https://github.com/Paulohmlf/Sistema-de-Balan-o.git
cd Sistema-de-Balan-o
````

### 2. Criar e Ativar o Ambiente Virtual

```bash
python -m venv venv
```

**No Windows:**

```bash
.\venv\Scripts\activate
```

**No macOS/Linux:**

```bash
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

**Exemplo de `requirements.txt`:**

```
Flask==2.3.3
pandas==2.1.3
openpyxl==3.1.2
Werkzeug==2.3.7
waitress==2.1.2
python-dotenv==1.0.0
google-generativeai==0.3.0
aiofiles==23.2.1
```

### 4. Configurar Variáveis de Ambiente

Crie um arquivo `.env` com:

```
FLASK_SECRET_KEY=sua_chave_aleatoria_segura
GEMINI_API_KEY=sua_api_key_do_google_gemini
```

### 5. Preparar o Banco de Dados

O sistema cria automaticamente o arquivo `inventario.db` e as tabelas na primeira execução, caso não existam.

Ele também tenta carregar dados de um arquivo Excel chamado `teste.xlsx`, localizado na raiz do projeto. Esse arquivo é **apenas um exemplo genérico com dados fictícios**, fornecido para demonstração inicial do sistema.

Caso deseje utilizar dados reais, substitua o `teste.xlsx` por um arquivo com a estrutura esperada:

* Aba chamada **`INVENTÁRIO`**
* Cabeçalho iniciando na **linha 15**
* Colunas mínimas esperadas:

  * `CÓDIGO`
  * `DESCRIÇÃO DO PRODUTO/SERVIÇO`
  * `FORNECEDOR`
  * `LOTE`
  * `QUANTIDADE`
  * `CONTROLE DE LOTE S/N`

**Atenção:** Se o arquivo estiver vazio ou fora do padrão esperado, o sistema pode não carregar corretamente os dados iniciais.

### 6. Executar o Sistema

**Modo desenvolvimento:**

```bash
python app.py
```

**Modo produção (Waitress):**

```bash
python run_waitress.py
```

Acesse: [http://127.0.0.1:5000](http://127.0.0.1:5000)

### 7. Criar Primeiro Usuário

Acesse: `http://127.0.0.1:5000/cadastro`

* Perfil **Gestor**: insira `Token de Gestor`: `Ranch@123`
* Perfil **Contador**: deixe o campo de token em branco

---

## 📂 Estrutura do Projeto

```
Sistema-de-Balan-o/
├── app.py
├── config.py
├── data_manager.py
├── run_waitress.py
├── requirements.txt
├── .env
├── inventario.db
├── teste.xlsx
├── backups/
├── routes/
│   ├── __init__.py
│   ├── auth.py
│   ├── chatbot.py
│   ├── contador.py
│   └── gestor.py
├── templates/
│   ├── *.html
└── utils/
    ├── __init__.py
    ├── async_operations.py
    ├── cache_manager.py
    └── database_pool.py
```

---

## ⚠️ Considerações de Segurança

* ❗ **Nunca exponha** `.env`, `inventario.db` ou planilhas sensíveis.
* ✅ Use `.gitignore` com:

  ```
  venv/
  __pycache__/
  .env
  *.db
  *.xlsx
  *.log
  ```
* ✅ Hash seguro de senhas com `pbkdf2:sha256`.
* ✅ SQL parametrizado (contra injeção).
* ✅ Validação de entrada no frontend e backend.
* 🔐 Altere o token de gestor `Ranch@123` para produção.

---

## 🤝 Contribuições

Contribuições são bem-vindas! Envie uma *issue* ou um *pull request* com sugestões, bugs ou melhorias.

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

---
