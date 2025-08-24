# bot_whatsapp.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

# --- Cargar bases de datos ---
try:
    df_pacientes = pd.read_excel("pacientes.xlsx", dtype={"Numero_Documento": str, "Departamento": str, "Ciudad": str})
    df_municipios = pd.read_excel("DaneMpios.xlsx", dtype={"CodigoDane": str})
    df_eps = pd.read_excel("EPS.xlsx", dtype={"Codigo_EPS": str})  # Nueva tabla
    print("✅ Bases de datos cargadas correctamente.")
except Exception as e:
    print(f"❌ Error al cargar archivos: {e}")
    exit()

# --- Obtener municipio ---
def obtener_municipio(cod_depto, cod_mpio):
    cod_depto = str(cod_depto).strip().zfill(2)
    cod_mpio = str(cod_mpio).strip().zfill(3)
    codigo_dane = cod_depto + cod_mpio

    print(f"🔍 Buscando municipio: {codigo_dane}")
    resultado = df_municipios[df_municipios["CodigoDane"] == codigo_dane]
    if not resultado.empty:
        return resultado.iloc[0]["Municipio"]
    return "Desconocido"

# --- Obtener nombre de EPS ---
def obtener_nombre_eps(codigo_eps):
    codigo_eps = str(codigo_eps).strip()
    resultado = df_eps[df_eps["Codigo_EPS"] == codigo_eps]
    if not resultado.empty:
        return resultado.iloc[0]["Nombre_EPS"]
    return "EPS no encontrada"

# --- Buscar paciente ---
def buscar_paciente(documento):
    documento = str(documento).strip().replace(" ", "").replace("-", "")
    resultado = df_pacientes[df_pacientes["Numero_Documento"] == documento]
    if not resultado.empty:
        p = resultado.iloc[0]
        municipio = obtener_municipio(p["Departamento"], p["Ciudad"])
        nombre_eps = obtener_nombre_eps(p["Codigo_EPS"])
        return {
            "nombre": f"{p['Primer_Nombre']} {p.get('Segundo_Nombre', '')} {p['Primer_Apellido']} {p.get('Segundo_Apellido', '')}".strip(),
            "regimen": p["REGIMEN"],
            "eps": nombre_eps,  # Ahora es el nombre, no el código
            "municipio": municipio
        }
    return None

# --- Flask ---
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    if "hola" in incoming_msg.lower():
        msg.body("Hola, bienvenido al centro de agendamiento virtual de Promesalud IPS, te acompañaré en tu proceso de asignación de cita. Por favor, ingresa tu número de documento:")
    else:
        # Si ya se envió el documento
        paciente = buscar_paciente(incoming_msg)
        if paciente:
            msg.body(f"Hola {paciente['nombre']}, según nuestros registros:\n"
                     f"📍 Vives en {paciente['municipio']}\n"
                     f"🏥 Régimen: {paciente['regimen']}\n"
                     f"💊 EPS: {paciente['eps']}\n\n"
                     f"¿Son correctos estos datos?\n"
                     f"1. SÍ\n"
                     f"2. NO")
        else:
            msg.body("Su número de identificación no se encuentra en base de datos. Por favor, acérquese a su EPS para actualizar su estado; fue un gusto atenderte.")

    return str(resp)

@app.route("/")
def home():
    return "Bot de salud activo 🟢"

# --- Iniciar ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)