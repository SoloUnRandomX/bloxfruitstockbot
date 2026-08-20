import time
import requests
import threading
from bs4 import BeautifulSoup
from flask import Flask

# =====================================================================
# CONFIGURACIÓN DEL WEB SERVER (Para engañar a Render)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Blox Fruits Activo 24/7"

# =====================================================================
# CONFIGURACIÓN DEL BOT DE WHATSAPP
# =====================================================================
URL_SEND_MESSAGE = "https://7107.api.greenapi.com/waInstance710722711148/sendMessage/a4b16e4933264bf9be8367b1ff5aeb01d81c2004a51c44faa1"
CHAT_ID = "120363410071554211@g.us"
URL_FRUITYBLOX = "https://fruityblox.com/stock"
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

ultimo_stock_registrado = {"normal": [], "mirage": []}

def limpiar_nombre_fruta(url_path):
    parte_nombre = url_path.split("/items/")[-1]
    nombre_limpio = parte_nombre.replace("-", " ").title()
    if "Fruit" not in nombre_limpio and nombre_limpio != "":
        nombre_limpio += " Fruit"
    return nombre_limpio

def obtener_y_procesar_stock():
    global ultimo_stock_registrado
    try:
        response = requests.get(URL_FRUITYBLOX, headers=HEADERS_WEB, timeout=15)
        if response.status_code != 200:
            return
            
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
            return

        stock_normal = sorted(list(set(stock_normal)))
        stock_mirage = sorted(list(set(stock_mirage)))

        if stock_normal == ultimo_stock_registrado["normal"] and stock_mirage == ultimo_stock_registrado["mirage"]:
            print(f"[{time.strftime('%H:%M:%S')}] Sin cambios en el stock.")
            return

        ultimo_stock_registrado["normal"] = stock_normal
        ultimo_stock_registrado["mirage"] = stock_mirage
            
        mensaje = "🍏 *¡EL STOCK SE HA ACTUALIZADO!* 🍎\n\n"
        mensaje += "🛒 *Stock Normal (Rotación 4h):*\n"
        for fruta in stock_normal: mensaje += f"• {fruta}\n"
        mensaje += "\n✨ *Stock Isla Mirage (Rotación 2h):*\n"
        for fruta in stock_mirage: mensaje += f"• {fruta}\n" if stock_mirage else "• Sin stock reportado.\n"
            
        requests.post(URL_SEND_MESSAGE, json={"chatId": CHAT_ID, "message": mensaje, "typingTime": 1000}, headers={'Content-Type': 'application/json'})
        print("¡Cambio detectado y enviado!")

    except Exception as e:
        print(f"Error: {e}")

def bucle_infinito_bot():
    print("Iniciando escaneo continuo de Blox Fruits...")
    obtener_y_procesar_stock()
    while True:
        obtener_y_procesar_stock()
        time.sleep(60)

# =====================================================================
# ARRANQUE EN PARALELO
# =====================================================================
if __name__ == "__main__":
    # Arrancamos el bot en un hilo secundario para que no interfiera con Flask
    hilo_bot = threading.Thread(target=bucle_infinito_bot, daemon=True)
    hilo_bot.start()
    
    # Arrancamos el servidor web que Render quiere ver (usa el puerto asignado por Render)
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
