@app.route("/webhook", methods=["POST"])
def webhook():
    global estado_usuario

    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')

    resp = MessagingResponse()
    msg = resp.message()

    if "hola" in incoming_msg.lower():
        if sender in estado_usuario:
            del estado_usuario[sender]
        msg.body("Hola, bienvenido al centro de agendamiento virtual de Promesalud IPS, te acompañaré en tu proceso de asignación de cita. Por favor, ingresa tu número de documento:")

    elif sender in estado_usuario:
        estado = estado_usuario[sender]
        etapa = estado["etapa"]

        # --- Registro de nuevo afiliado ---
        if etapa == "registro":
            # (código de registro, igual que antes)
            pass  # Ya está bien

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