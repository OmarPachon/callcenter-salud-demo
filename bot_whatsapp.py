# bot_whatsapp.py
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import pandas as pd
import os

# --- Flask ---
# ✅ Definimos 'app' ANTES de cualquier @app.route
app = Flask(__name__)

# --- Cargar bases de datos ---
try:
    df_pacientes = pd.read_excel("pacientes.xlsx", dtype={"Numero_Documento": str, "Departamento": str, "Ciudad": str})
    df_municipios = pd.read_excel("DaneMpios.xlsx", dtype={"CodigoDane": str})
    df_eps = pd.read_excel("EPS.xlsx", dtype={"Codigo_EPS": str})
    print("✅ Bases de datos cargadas correctamente.")
except Exception as e:
    print(f"❌ Error al cargar archivos: {e}")
    exit()

# --- Obtener municipio ---
def obtener_municipio(cod_depto, cod_mpio):
    cod_depto = str(cod_depto).strip().zfill(2)
    cod_mpio = str(cod_mpio).strip().zfill(3)
    codigo_dane = cod_depto + cod_mpio
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
    
    # ✅ CORRECCIÓN: empty es un atributo, no una función → sin ()
    if not resultado.empty:
        p = resultado.iloc[0]
        municipio = obtener_municipio(p["Departamento"], p["Ciudad"])
        nombre_eps = obtener_nombre_eps(p["Codigo_EPS"])
        return {
            "nombre": f"{p['Primer_Nombre']} {p.get('Segundo_Nombre', '')} {p['Primer_Apellido']} {p.get('Segundo_Apellido', '')}".strip(),
            "regimen": p["REGIMEN"],
            "eps": nombre_eps,
            "municipio": municipio
        }
    return None

# --- Guardar nuevo paciente en Excel ---
def guardar_nuevo_paciente(datos):
    nuevo = {
        "Numero_Documento": datos["documento"],
        "Primer_Nombre": datos["primer_nombre"],
        "Segundo_Nombre": datos.get("segundo_nombre", ""),
        "Primer_Apellido": datos["primer_apellido"],
        "Segundo_Apellido": datos.get("segundo_apellido", ""),
        "REGIMEN": datos["regimen"],
        "Codigo_EPS": datos["codigo_eps"],
        "Departamento": "00",
        "Ciudad": "000"
    }
    df_nuevo = pd.DataFrame([nuevo])
    try:
        with pd.ExcelWriter("pacientes.xlsx", mode="a", if_sheet_exists="overlay", engine="openpyxl") as writer:
            df_nuevo.to_excel(writer, index=False, header=False, startrow=writer.sheets["Sheet1"].max_row)
        print(f"✅ Nuevo paciente guardado: {nuevo['Primer_Nombre']} {nuevo['Primer_Apellido']} (Documento: {nuevo['Numero_Documento']})")
    except Exception as e:
        print(f"❌ Error al guardar en Excel: {e}")

# --- Estado del usuario ---
estado_usuario = {}

# --- Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    global estado_usuario

    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')  # Ej: whatsapp:+573006503959

    resp = MessagingResponse()
    msg = resp.message()

    # --- Lógica del bot ---
    if "hola" in incoming_msg.lower():
        # Reiniciar estado
        if sender in estado_usuario:
            del estado_usuario[sender]

        msg.body("Hola, bienvenido al centro de agendamiento virtual de Promesalud IPS, te acompañaré en tu proceso de asignación de cita. Por favor, ingresa tu número de documento:")

    elif sender in estado_usuario:
        estado = estado_usuario[sender]
        etapa = estado["etapa"]

        # --- Registro de nuevo afiliado ---
        if etapa == "registro":
            paso = estado["paso"]

            if paso == "primer_nombre":
                estado["primer_nombre"] = incoming_msg
                estado["paso"] = "segundo_nombre"
                msg.body("Gracias. Ahora tu segundo nombre (si no tienes, escribe 'N/A'):")

            elif paso == "segundo_nombre":
                estado["segundo_nombre"] = incoming_msg
                estado["paso"] = "primer_apellido"
                msg.body("Ahora tu primer apellido:")

            elif paso == "primer_apellido":
                estado["primer_apellido"] = incoming_msg
                estado["paso"] = "segundo_apellido"
                msg.body("Ahora tu segundo apellido (si no tienes, escribe 'N/A'):")

            elif paso == "segundo_apellido":
                estado["segundo_apellido"] = incoming_msg

                # Si es Sanitas, pregunta régimen
                if estado["codigo_eps"] == "100100":  # Sanitas
                    estado["paso"] = "regimen_sanitas"
                    msg.body("¿Cuál es tu régimen?\n1. Subsidiado\n2. Contributivo")
                else:  # Magisterio → régimen especial
                    estado["regimen"] = "Especial"
                    guardar_nuevo_paciente(estado)
                    del estado_usuario[sender]
                    msg.body("✅ Registrado como afiliado al Magisterio (Régimen: Especial). Vuelve a enviar 'hola' para continuar.")

            elif paso == "regimen_sanitas":
                if incoming_msg == "1":
                    estado["regimen"] = "Subsidiado"
                elif incoming_msg == "2":
                    estado["regimen"] = "Contributivo"
                else:
                    msg.body("Por favor, responde con 1 o 2.")
                    return str(resp)

                guardar_nuevo_paciente(estado)
                del estado_usuario[sender]
                msg.body(f"✅ Registrado como afiliado a {estado['eps_nombre']} (Régimen: {estado['regimen']}). Vuelve a enviar 'hola' para continuar.")

        # --- Preguntar EPS si no se encontró el documento ---
        elif etapa == "preguntar_eps":
            if incoming_msg == "3":
                msg.body("Gracias por tu respuesta. No podemos continuar sin estar en nuestra base de datos. Acércate a tu EPS para actualizarte. ¡Hasta luego!")
                del estado_usuario[sender]
            elif incoming_msg in ["1", "2"]:
                eps_nombre = "E.P.S. Sanitas S.A." if incoming_msg == "1" else "FONDO DE PRESTACIONES SOCIALES DEL MAGISTERIO"
                codigo_eps = "100100" if incoming_msg == "1" else "100200"

                estado_usuario[sender] = {
                    "etapa": "registro",
                    "paso": "primer_nombre",
                    "documento": estado["documento"],
                    "eps_nombre": eps_nombre,
                    "codigo_eps": codigo_eps,
                    "regimen": None
                }
                msg.body(f"Gracias. Ahora te registraremos. Por favor, ingresa tu primer nombre:")
            else:
                msg.body("Por favor, responde con 1, 2 o 3.")

    else:
        # --- Búsqueda inicial del paciente ---
        paciente = buscar_paciente(incoming_msg)
        if paciente:
            estado_usuario[sender] = {
                "etapa": "datos_confirmados",
                "documento": incoming_msg
            }
            msg.body(f"Hola {paciente['nombre']}, según nuestros registros:\n"
                     f"📍 Vives en {paciente['municipio']}\n"
                     f"🏥 Régimen: {paciente['regimen']}\n"
                     f"💊 EPS: {paciente['eps']}\n\n"
                     f"¿Son correctos estos datos?\n"
                     f"1. SÍ\n"
                     f"2. NO")
        else:
            # Primer intento fallido
            if sender not in estado_usuario:
                estado_usuario[sender] = {
                    "etapa": "reintentar_documento",
                    "documento": incoming_msg
                }
                msg.body("No encontramos tu documento. Por favor, vuelve a ingresarlo para verificarlo.")
            else:
                # ✅ Corrección: Asegurarnos de que no se sobrescriba
                # Si ya está en reintentar, y vuelve a enviar un documento, pasamos a preguntar EPS
                if estado_usuario[sender]["etapa"] == "reintentar_documento":
                    estado_usuario[sender]["etapa"] = "preguntar_eps"
                    msg.body("Tu número de identificación no se encuentra en nuestra base de datos.\n\n"
                             "¿Eres afiliado a una de estas EPS?\n"
                             "1. E.P.S. Sanitas S.A.\n"
                             "2. FONDO DE PRESTACIONES SOCIALES DEL MAGISTERIO\n"
                             "3. NINGUNA DE LAS ANTERIORES\n\n"
                             "Por favor, responde con el número de la opción.")
                else:
                    msg.body("Por favor, responde con la opción correcta.")

    return str(resp)

# --- Ruta de prueba ---
@app.route("/")
def home():
    return "Bot de salud activo 🟢"

# --- Iniciar servidor ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)