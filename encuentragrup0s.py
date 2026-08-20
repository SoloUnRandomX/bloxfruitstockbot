import os
import json
import time
import requests
import threading
from bs4 import BeautifulSoup
from flask import Flask, render_template_string, jsonify

# =====================================================================
# CONFIGURACIÓN DEL WEB SERVER (Flask)
# =====================================================================
app = Flask(__name__)

ARCHIVO_MEMORIA = os.path.join(os.path.dirname(__file__), "stock_memoria.json")

def cargar_memoria_local():
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"normal": [], "mirage": []}

def guardar_memoria_local(nuevo_stock):
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(nuevo_stock, f, ensure_ascii=False, indent=4)

HTML_PLANTILLA = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blox Fruits Stock Tracker</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #121214; color: #e1e1e6; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .container { max-width: 600px; width: 100%; background: #202024; padding: 30px; border-radius: 12px; box-sizing: border-box; }
        h1 { text-align: center; color: #00b37e; margin-top: 0; font-size: 24px; }
        h2 { border-bottom: 2px solid #29292e; padding-bottom: 8px; font-size: 18px; margin-top: 25px; }
        .normal-title { color: #4895ef; }
        .mirage-title { color: #f72585; }
        ul { list-style: none; padding: 0; margin: 0; }
        li { padding: 10px 15px; background: #29292e; margin-bottom: 8px; border-radius: 6px; display: flex; align-items: center; font-weight: 500; }
        li::before { content: "•"; color: #00b37e; margin-right: 10px; font-weight: bold; }
        .empty { color: #7c7c8a; font-style: italic; }
        .btn-container { text-align: center; margin-top: 25px; }
        .btn-send { background-color: #00b37e; color: #ffffff; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; width: 100%; }
        .btn-send:disabled { background-color: #7c7c8a; cursor: not-allowed; }
        .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #7c7c8a; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🍏 Blox Fruits Stock Tracker 🍎</h1>
        <h2 class="normal-title">🛒 Stock Normal (Rotación 4h)</h2>
        <ul>
            {% if stock.normal %}
                {% for fruta in stock.normal %}
                    <li>{{ fruta }}</li>
                {% endfor %}
            {% else %}
                <li class="empty">Cargando datos del distribuidor o inventario vacío...</li>
            {% endif %}
        </ul>
        <h2 class="mirage-title">✨ Stock Isla Mirage (Rotación 2h)</h2>
        <ul>
            {% if stock.mirage %}
                {% for fruta in stock.mirage %}
                    <li>{{ fruta }}</li>
                {% endfor %}
            {% else %}
                <li class="empty">Isla Mirage no activa o sin stock reportado.</li>
            {% endif %}
        </ul>
        <div class="btn-container">
            <button id="sendBtn" class="btn-send" onclick="forzarEnvioWhatsApp()">📲 Mandar Stock al Grupo</button>
        </div>
        <div class="footer">Monitoreo automático en tiempo real.</div>
    </div>
    <script>
        function forzarEnvioWhatsApp() {
            const btn = document.getElementById('sendBtn');
            btn.disabled = true;
            btn.innerText = '⏳ Enviando petición...';
            fetch('/send-now')
                .then(response => response.json())
                .then(data => {
                    if (data.success) { btn.innerText = '✅ ¡Enviado con éxito!'; }
                    else { btn.innerText = '❌ Error al enviar'; }
                    setTimeout(() => { btn.disabled = false; btn.innerText = '📲 Mandar Stock al Grupo'; }, 4000);
                })
                .catch(error => {
                    btn.innerText = '❌ Error de red';
                    setTimeout(() => { btn.disabled = false; btn.innerText = '📲 Mandar Stock al Grupo'; }, 4000);
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    stock_actual = cargar_memoria_local()
    return render_template_string(HTML_PLANTILLA, stock=stock_actual)

@app.route('/send-now')
def send_now():
    resultado = obtener_y_procesar_stock(forzar=True)
    if resultado:
        return jsonify({"success": True})
    return jsonify({"success": False})

# =====================================================================
# CONFIGURACIÓN DEL BOT DE WHATSAPP (Lógica de Fondo)
# =====================================================================
URL_SEND_MESSAGE = "https://7107.api.greenapi.com/waInstance710722711148/sendMessage/a4b16e4933264bf9be8367b1ff5aeb01d81c2004a51c44faa1"
CHAT_ID = "120363410071554211@g.us"
URL_FRUITYBLOX = "https://fruityblox.com/stock"
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def limpiar_nombre_fruta(url_path):
    parte_nombre = url_path.split("/items/")[-1]
    nombre_limpio = parte_nombre.replace("-", " ").title()
    if "Fruit" not in nombre_limpio and nombre_limpio != "":
        nombre_limpio += " Fruit"
    return nombre_limpio

def obtener_y_procesar_stock(forzar=False):
    ultimo_stock_registrado = cargar_memoria_local()
    try:
        response = requests.get(URL_FRUITYBLOX, headers=HEADERS_WEB, timeout=15)
        if response.status_code != 200:
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        secciones = soup.find_all('section')
        
        stock_normal = []
        stock_mirage = []
        
        for seccion in secciones:
            titulo = seccion.find(['h1', 'h2', 'h3'])
            if not titulo: continue
            texto_titulo = titulo.text.strip().lower()
            tarjetas = seccion.find_all('a', href=lambda href: href and "/items/" in href)
            
            for tarjeta in tarjetas:
                nombre = limpiar_nombre_fruta(tarjeta.get('href'))
                if nombre:
                    if "normal" in texto_titulo or "dealer" in texto_titulo:
                        stock_normal.append(nombre)
                    elif "mirage" in texto_titulo or "advanced" in texto_titulo:
                        stock_mirage.append(nombre)

        if not stock_normal and not stock_mirage:
            for div in soup.find_all('div', class_=lambda c: c and ('stock' in c.lower() or 'card' in c.lower())):
                texto_div = div.text.strip().lower()
                tarjetas_div = div.find_all('a', href=lambda href: href and "/items/" in href)
                for t in tarjetas_div:
                    fruta_nombre = limpiar_nombre_fruta(t.get('href'))
                    if "mirage" in texto_div:
                        stock_mirage.append(fruta_nombre)
                    else:
                        stock_normal.append(fruta_nombre)

        if not stock_normal and not stock_mirage:
            return False

        stock_normal = sorted(list(set(stock_normal)))
        stock_mirage = sorted(list(set(stock_mirage)))

        if not forzar:
            if stock_normal == ultimo_stock_registrado["normal"] and stock_mirage == ultimo_stock_registrado["mirage"]:
                return True

        nuevo_estado = {"normal": stock_normal, "mirage": stock_mirage}
        guardar_memoria_local(nuevo_estado)
            
        # Formateo ultra-limpio en una sola línea para evitar fallos de renderizado
        encabezado = "⚡ *[FORZADO] STOCK ACTUAL DEL MERCADO* ⚡\n\n" if forzar else "🍏 *¡EL STOCK SE HA ACTUALIZADO!* 🍎\n\n"
        mensaje = encabezado
        
        mensaje += "🛒 *Stock Normal (Rotación 4h):*\n"
        for fruta in stock_normal:
            mensaje += f"• {fruta}\n"
            
        mensaje += "\n✨ *Stock Isla Mirage (Rotación 2h):*\n"
        if stock_mirage:
            for fruta in stock_mirage:
                mensaje += f"• {fruta}\n"
        else:
            mensaje += "• Sin stock reportado.\n"
            
        requests.post(URL_SEND_MESSAGE, json={"chatId": CHAT_ID, "message": mensaje, "typingTime": 1000}, headers={'Content-Type': 'application/json'})
        return True

    except Exception as e:
        print(f"Error en procesamiento: {e}")
        return False

def bucle_infinito_bot():
    print("Iniciando escaneo continuo de Blox Fruits...")
    obtener_y_procesar_stock(forzar=False)
    while True:
        obtener_y_procesar_stock(forzar=False)
        time.sleep(60)

if __name__ == "__main__":
    hilo_bot = threading.Thread(target=bucle_infinito_bot, daemon=True)
    hilo_bot.start()
    
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
