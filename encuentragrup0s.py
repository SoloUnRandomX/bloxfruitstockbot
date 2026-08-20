import time
import requests
import threading
from bs4 import BeautifulSoup

# =====================================================================
# CONFIGURACIÓN DEL BOT (Tus datos exactos)
# =====================================================================
URL_SEND_MESSAGE = "https://7107.api.greenapi.com/waInstance710722711148/sendMessage/a4b16e4933264bf9be8367b1ff5aeb01d81c2004a51c44faa1"
CHAT_ID = "120363410071554211@g.us"  # Tu grupo de amigos

URL_FRUITYBLOX = "https://fruityblox.com/stock"
HEADERS_WEB = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Variable en memoria para recordar el stock anterior
ultimo_stock_registrado = {"normal": [], "mirage": []}

def limpiar_nombre_fruta(url_path):
    """Convierte un enlace tipo '/items/light-fruit' en 'Light Fruit'"""
    parte_nombre = url_path.split("/items/")[-1]
    # Reemplaza guiones por espacios y pone las mayúsculas iniciales
    nombre_limpio = parte_nombre.replace("-", " ").title()
    # Corrección estética para la palabra 'Fruit' si la incluye la URL
    if "Fruit" not in nombre_limpio and nombre_limpio != "":
        nombre_limpio += " Fruit"
    return nombre_limpio

def obtener_stock_fruityblox(forzar=False):
    global ultimo_stock_registrado
    try:
        response = requests.get(URL_FRUITYBLOX, headers=HEADERS_WEB, timeout=15)
        if response.status_code != 200:
            print(f"\n[FruityBlox] Error de conexión: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        secciones = soup.find_all('section')
        
        stock_normal = []
        stock_mirage = []
        
        for seccion in secciones:
            titulo_h2 = seccion.find('h2')
            if not titulo_h2:
                continue
                
            nombre_seccion = titulo_h2.text.strip().lower()
            
            # Buscamos todos los enlaces que contengan '/items/' en su atributo href
            tarjetas = seccion.find_all('a', href=lambda href: href and "/items/" in href)
            
            for tarjeta in tarjetas:
                url_href = tarjeta.get('href')
                nombre_fruta = limpiar_nombre_fruta(url_href)
                
                if nombre_fruta:
                    if "normal" in nombre_seccion:
                        stock_normal.append(nombre_fruta)
                    elif "mirage" in nombre_seccion:
                        stock_mirage.append(nombre_fruta)
                        
        # Si fallan ambos almacenes, hacemos un escaneo de emergencia buscando cualquier fruta en la página
        if not stock_normal and not stock_mirage:
            enlaces_globales = soup.find_all('a', href=lambda href: href and "/items/" in href)
            if enlaces_globales:
                print("\n[FruityBlox] Modo de compatibilidad activado: Estructura de secciones modificada.")
                for enlace in enlaces_globales:
                    stock_normal.append(limpiar_nombre_fruta(enlace.get('href')))

        if not stock_normal and not stock_mirage:
            print("\n[FruityBlox] No se detectó ninguna fruta en el documento HTML.")
            return None

        # Quitamos duplicados y ordenamos las listas
        stock_normal = sorted(list(set(stock_normal)))
        stock_mirage = sorted(list(set(stock_mirage)))

        if not forzar:
            if stock_normal == ultimo_stock_registrado["normal"] and stock_mirage == ultimo_stock_registrado["mirage"]:
                return False

        ultimo_stock_registrado["normal"] = stock_normal
        ultimo_stock_registrado["mirage"] = stock_mirage
            
        encabezado = "⚡ *STOCK ACTUAL* ⚡\n\n" if forzar else "🍏 *¡EL STOCK SE HA ACTUALIZADO!* 🍎\n\n"
        mensaje = encabezado
        
        mensaje += "🛒 *Stock Normal:*\n"
        if stock_normal:
            for fruta in stock_normal:
                mensaje += f"• {fruta}\n"
        else:
            mensaje += "• No se detectaron frutas.\n"
        
        mensaje += "\n✨ *Stock Isla Mirage:*\n"
        if stock_mirage:
            for fruta in stock_mirage:
                mensaje += f"• {fruta}\n"
        else:
            mensaje += "• Isla Mirage no activa o sin stock reportado.\n"
            
        return mensaje

    except Exception as e:
        print(f"\n[FruityBlox] Error al procesar: {e}")
        return None

def enviar_mensaje_whatsapp(texto_reporte):
    payload = {
        "chatId": CHAT_ID, 
        "message": texto_reporte, 
        "typingTime": 1000 
    }
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(URL_SEND_MESSAGE, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"\n[{time.strftime('%H:%M:%S')}] ¡Mensaje enviado a WhatsApp correctamente!")
        else:
            print(f"\n[Green API] Error ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"\n[Green API] Error de conexión HTTP: {e}")

def escuchar_consola():
    while True:
        comando = input().strip()
        
        if comando.lower() == "/send":
            print("\n[Consola] Comando /send recibido. Obteniendo stock actual...")
            reporte_forzado = obtener_stock_fruityblox(forzar=True)
            if reporte_forzado:
                enviar_mensaje_whatsapp(reporte_forzado)
            else:
                print("[Consola] No se pudo obtener el stock para enviar.")
        else:
            print(f"[Consola] Comando '{comando}' no reconocido. Escribe /send para forzar el envío.")

def ejecutar_bot():
    print("Bot de FruityBlox con comando de consola activado.")
    print("Estableciendo base de datos inicial silenciosa...")
    obtener_stock_fruityblox(forzar=False)
    print("Vigilando cambios de stock en la web. Puedes escribir /send aquí en cualquier momento:\n")
    
    hilo_consola = threading.Thread(target=escuchar_consola, daemon=True)
    hilo_consola.start()
    
    while True:
        reporte_automatico = obtener_stock_fruityblox(forzar=False)
        print(reporte_automatico)
        
        if reporte_automatico is False:
            print(f"[{time.strftime('%H:%M:%S')}] Escaneo automático: Sin cambios.", end="\r")
        elif reporte_automatico:
            enviar_mensaje_whatsapp(reporte_automatico)
            
        time.sleep(60)

if __name__ == "__main__":
    ejecutar_bot()
