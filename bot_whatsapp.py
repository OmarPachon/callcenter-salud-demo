# bot_whatsapp.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

# --- Cargar bases de datos ---
try:
    df_pacientes = pd.read_excel("pacientes.xlsx", dtype={"Numero_Documento": str, "Departamento": str, "Ciudad": str})
    print("✅ pacientes.xlsx cargado correctamente.")
except Exception as e:
    print(f"❌ Error al cargar pacientes.xlsx: {e}")
    exit()

try:
    df_municipios = pd.read_excel("DaneMpios.xlsx", dtype={"CodigoDane": str})
    print("✅ DaneMpios.xlsx cargado correctamente.")
except Exception as e:
    print(f"❌ Error al cargar DaneMpios.xlsx: {e}")
    exit()

# --- Obtener nombre del municipio ---
def obtener_municipio(cod_depto, cod_mpio):
    cod_depto = str(cod_depto).strip().zfill(2)
    cod_mpio = str(cod_mpio).strip().zfill(3)
    codigo_dane = cod_depto + cod_mpio

    resultado = df_municipios[df_municipios["CodigoDane"] == codigo_dane]
    if not resultado.empty:
        return resultado.iloc[0]["Municipio"]
    return "Desconocido"

# --- Buscar paciente ---
def buscar_paciente(documento):
    documento = str(documento).strip().replace(" ", "").replace("-", "")
    resultado = df_pacientes[df_pacientes["Numero_Documento"] == documento]
    if not resultado.empty:
        p = resultado.iloc[0]
        municipio = obtener_municipio(p["Departamento"], p["Ciudad"])
        return {
            "nombre": f"{p['Primer_Nombre']} {p.get('Segundo_Nombre', '')} {p['Primer_Apellido']} {p.get('Segundo_Apellido', '')}".strip(),
            "regimen": p["REGIMEN"],
            "eps": p["Codigo_EPS"],
            "municipio": municipio
        }
    return None

# --- Iniciar Flask ---
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    if "hola" in incoming_msg.lower():
        msg.body("Hola, bienvenido al centro de salud. Por favor, envía tu número de documento:")
    else:
        paciente = buscar_paciente(incoming_msg)
        if paciente:
            msg.body(f"Hola {paciente['nombre']}, según nuestros registros:\n"
                     f"📍 Vives en {paciente['municipio']}\n"
                     f"🏥 Régimen: {paciente['regimen']}\n"
                     f"💊 EPS: {paciente['eps']}\n\n"
                     f"¿Son correctos estos datos? Responde SÍ o NO.")
        else:
            msg.body("No encontramos tu documento. Por favor, verifica el número o contacta a nuestro personal.")

    return str(resp)

@app.route("/")
def home():
    return "Bot de salud activo 🟢"

# --- Iniciar servidor (para Render)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)