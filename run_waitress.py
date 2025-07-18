# run_waitress.py
from waitress import serve
from app import create_app # Importa a função create_app do seu app.py

# Cria a instância da aplicação Flask
app = create_app()

print("Iniciando Waitress para a aplicação Flask...")
# Serve a aplicação Flask usando Waitress
# host='0.0.0.0' permite que ela seja acessível externamente (pelo Ngrok)
# port=5000 é a porta que sua aplicação Flask escutará localmente
serve(app, host='0.0.0.0', port=5000)