import requests
from bs4 import BeautifulSoup
from rapidfuzz import process
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import time
import os

TOKEN = os.environ.get("TOKEN")
URL = "https://kworb.net/spotify/listeners.html"

# ---------- CACHE ----------
cache_datos = {}
ultima_actualizacion = 0
CACHE_TIEMPO = 300  # 5 minutos


def obtener_datos():
    global cache_datos, ultima_actualizacion

    if time.time() - ultima_actualizacion < CACHE_TIEMPO and cache_datos:
        return cache_datos

    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    tabla = soup.find("table")
    filas = tabla.find_all("tr")[1:]

    artistas = {}

    for fila in filas:
        columnas = fila.find_all("td")
        if len(columnas) >= 6:
            posicion = columnas[0].text.strip()
            nombre = columnas[1].text.strip()
            oyentes = columnas[2].text.strip()
            cambio = columnas[3].text.strip()
            peak_pos = columnas[4].text.strip()
            peak_oyentes = columnas[5].text.strip()

            artistas[nombre.lower()] = {
                "nombre": nombre,
                "posicion": posicion,
                "oyentes": oyentes,
                "cambio": cambio,
                "peak_pos": peak_pos,
                "peak_oyentes": peak_oyentes
            }

    cache_datos = artistas
    ultima_actualizacion = time.time()

    return artistas


def buscar_artista(nombre, artistas):
    nombres = list(artistas.keys())
    resultado = process.extractOne(nombre.lower(), nombres)
    if resultado:
        return artistas[resultado[0]]
    return None


# ---------- COMANDOS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
🤖 BOT SPOTIFY LISTENERS

Comandos disponibles:

/artista nombre
/posicion nombre
/oyentes nombre
/cambio nombre
/peak_oyentes nombre
/peak_posicion nombre
/comparar artista1 vs artista2
/quien numero
/top numero

Ejemplo:
/artista bad bunny
/comparar bad bunny vs drake
"""
    await update.message.reply_text(mensaje)


async def artista(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())

    if datos:
        mensaje = f"""
📊 {datos['nombre']}

Posición actual: {datos['posicion']}
Oyentes mensuales: {datos['oyentes']}
Cambio diario: {datos['cambio']}
Peak posición: {datos['peak_pos']}
Peak oyentes: {datos['peak_oyentes']}
"""
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("Artista no encontrado")


async def comparar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = " ".join(context.args)

    if "vs" not in texto:
        await update.message.reply_text("Usa el formato: /comparar artista1 vs artista2")
        return

    nombre1, nombre2 = texto.split("vs")
    datos = obtener_datos()

    artista1 = buscar_artista(nombre1.strip(), datos)
    artista2 = buscar_artista(nombre2.strip(), datos)

    if artista1 and artista2:
        mensaje = f"""
⚔️ COMPARACIÓN

🎤 {artista1['nombre']}
Posición: {artista1['posicion']}
Oyentes: {artista1['oyentes']}
Cambio diario: {artista1['cambio']}
Peak posición: {artista1['peak_pos']}
Peak oyentes: {artista1['peak_oyentes']}

VS

🎤 {artista2['nombre']}
Posición: {artista2['posicion']}
Oyentes: {artista2['oyentes']}
Cambio diario: {artista2['cambio']}
Peak posición: {artista2['peak_pos']}
Peak oyentes: {artista2['peak_oyentes']}
"""
        await update.message.reply_text(mensaje)
    else:
        await update.message.reply_text("Uno o ambos artistas no fueron encontrados")


async def posicion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())
    if datos:
        await update.message.reply_text(f"{datos['nombre']} está en la posición {datos['posicion']}")
    else:
        await update.message.reply_text("Artista no encontrado")


async def oyentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())
    if datos:
        await update.message.reply_text(f"{datos['nombre']} tiene {datos['oyentes']} oyentes mensuales")
    else:
        await update.message.reply_text("Artista no encontrado")


async def cambio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())
    if datos:
        await update.message.reply_text(f"Cambio diario de {datos['nombre']}: {datos['cambio']}")
    else:
        await update.message.reply_text("Artista no encontrado")


async def peak_oyentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())
    if datos:
        await update.message.reply_text(f"Peak de oyentes de {datos['nombre']}: {datos['peak_oyentes']}")
    else:
        await update.message.reply_text("Artista no encontrado")


async def peak_posicion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = " ".join(context.args)
    datos = buscar_artista(nombre, obtener_datos())
    if datos:
        await update.message.reply_text(f"Peak de posición de {datos['nombre']}: {datos['peak_pos']}")
    else:
        await update.message.reply_text("Artista no encontrado")

async def quien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Devuelve el artista que está en la posición indicada"""
    if not context.args:
        await update.message.reply_text("Usa: /quien [posición]")
        return

    try:
        posicion_buscada = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Debes escribir un número válido")
        return

    artistas = obtener_datos()
    for artista in artistas.values():
        if artista['posicion'].isdigit() and int(artista['posicion']) == posicion_buscada:
            await update.message.reply_text(f"La posición {posicion_buscada} es {artista['nombre']}")
            return

    await update.message.reply_text(f"No se encontró ningún artista en la posición {posicion_buscada}")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Devuelve un top N de artistas"""
    if not context.args:
        await update.message.reply_text("Usa: /top [número]")
        return

    try:
        n = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Debes escribir un número válido")
        return

    artistas = obtener_datos()
    # Ordenamos por posición
    artistas_ordenados = sorted(
        artistas.values(),
        key=lambda x: int(x['posicion']) if x['posicion'].isdigit() else 999999
    )

    n = min(n, len(artistas_ordenados))
    mensaje = ""
    for i in range(n):
        mensaje += f"{i+1}. {artistas_ordenados[i]['nombre']}\n"

    await update.message.reply_text(mensaje)
# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("artista", artista))
    app.add_handler(CommandHandler("comparar", comparar))
    app.add_handler(CommandHandler("posicion", posicion))
    app.add_handler(CommandHandler("oyentes", oyentes))
    app.add_handler(CommandHandler("cambio", cambio))
    app.add_handler(CommandHandler("peak_oyentes", peak_oyentes))
    app.add_handler(CommandHandler("peak_posicion", peak_posicion))
    app.add_handler(CommandHandler("quien", quien))
    app.add_handler(CommandHandler("top", top))

    print("Bot funcionando...")
    app.run_polling()


if __name__ == "__main__":
    main()
