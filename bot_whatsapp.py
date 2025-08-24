# bot_whatsapp.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

# --- PASO 1: Cargar las bases de datos ---
try:
    # Base de pacientes
    df_pacientes = pd.read_excel("pacientes.xlsx", dtype={"Numero_Documento": str, "Departamento": str, "Ciudad": str})
    print("✅ pacientes.xlsx cargado correctamente.")

    # Base de municipios (DANE)
    df_municipios = pd.read_excel("DaneMpios.xlsx", dtype={"CodigoDane": str})
    print("✅ DaneMpios.xlsx cargado correctamente.")
except Exception as e:
    print(f"❌ Error al cargar los archivos: {e}")
    exit()

# --- PASO 2: Función para obtener el nombre del municipio ---
def obtener_municipio(cod_depto, cod_mpio):
    # Asegurar formato correcto
    cod_depto = str(cod_depto).strip().zfill(2)  # "5" → "05"
    cod_mpio = str(cod_mpio).strip().zfill(3)    # "1" → "001"
    codigo_dane = cod_depto + cod_mpio            # "05" + "001" → "05001"

    # 🔍 Depuración: ver qué código se está formando
    print(f"🔍 FORMANDO CÓDIGO DANE")
    print(f"   Departamento: '{cod_depto}'")
    print(f"   Ciudad: '{cod_mpio}'")
    print(f"   Código Dane completo: '{codigo_dane}'")

    # Buscar en DaneMpios
    resultado = df_municipios[df_municipios["CodigoDane"] == codigo_dane]
    
    if not resultado.empty:
        municipio = resultado.iloc[0]["Municipio"]
        print(f"   ✅ Municipio encontrado: {municipio}")
        return municipio
    else:
        print(f"   ❌ No se encontró el municipio para {codigo_dane}")
        return "Desconocido"

# --- PASO 3: Función para buscar paciente ---
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

# --- PASO 4: Iniciar Flask ---
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    # --- Lógica del bot ---
    if "hola" in incoming_msg.lower():
        msg.body("Hola, bienvenido al centro de agendamiento virtual de Promesalud IPS, te acompañaré en tu proceso de asignación de cita. Por favor, ingresa tu número de documento:")
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

# --- Ruta de prueba ---
@app.route("/")
def home():
    return "Bot de salud activo 🟢"

# --- Iniciar servidor ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)