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
