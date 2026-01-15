import streamlit as st
import pandas as pd
import datetime
from io import StringIO

DATA_TYPES = {
    "Texto": str,
    "Entero": int,
    "Decimal": float,
    "Booleano": "bool",
    "Fecha (AAAA-MM-DD)": "date",
    "Email (@)": "email"
}

CHANNEL_TYPES_VALIDOS = [
    "EMAIL",
    "SMS",
    "APNS",
    "APNS_SANDBOX",
    "GCM",
    "CUSTOM"
]

def is_valid(value, expected_type):
    if pd.isna(value) or value == "":
        return False
    try:
        if expected_type == str:
            return isinstance(value, str)
        elif expected_type == int:
            return float(value).is_integer()
        elif expected_type == float:
            float(value)
            return True
        elif expected_type == "bool":
            return str(value).strip().lower() in ['true', 'false']
        elif expected_type == "date":
            datetime.datetime.strptime(str(value), "%Y-%m-%d")
            return True
        elif expected_type == "email":
            return "@" in str(value)
    except:
        return False
    return False

def main():
    st.title("🔍 Validador carga de bases manuales")

    st.markdown("""
    ### ℹ️ Consideraciones importantes:
    - El archivo debe estar en formato `.csv CSV (delimitado por comas)` o `.csv CSV UTF-8 (delimitado por comas)`
    - El contenido del archivo CSV al abrir en Excel debe estar todo en la primera columna (no separado por columnas)
    - El separador correcto de columnas y campos a utilizar es **coma (`,`)**. Por cada coma detectada, será interpretada como dato de diferentes columnas, por ej.: Gutierrez, Giuliana será interpretado como Gutierrez para una columna y Giuliana para la siguiente.
    - El nombre de las columnas debe corresponder a alguno de los siguientes prefijos `User.UserId` `User.UserAttributes.NombreColumnaCamelCase`
    - Los emails pueden pertenecer a cualquier dominio
    - Las fechas deben tener el formato **AAAA-MM-DD**
    - Seleccioná el tipo de dato esperado por cada columna antes de validar
    - Si en una columna es obligatorio que exista dato, es decir no sea nulo, marcala como tal para que se detecten campos vacíos.
    - El proyecto destino "Prospectos" exige las columnas ChannelType y Address, para "SPV_Marketing" no es obligatorio.
    """)
    if "ignorar_sobrantes" not in st.session_state:
        st.session_state.ignorar_sobrantes = False
    uploaded_file = st.file_uploader("📂 Subí tu archivo CSV", type="csv")

    if uploaded_file is not None:
        error_critico = False
        separator = ","

        st.subheader("📌 Proyecto destino")

        proyecto = st.selectbox(
            "Seleccioná el proyecto al cual se va a importar la base:",
            ["Prospectos", "SPV_Marketing"]
        )

        st.info(f"Proyecto seleccionado: **{proyecto}**")

        if proyecto == "Prospectos":
            COLUMNAS_OBLIGATORIAS_ENCABEZADO = ["ChannelType", "Address"]
            COLUMNAS_OBLIGATORIAS_POR_FILA = ["ChannelType"]
        else:  # SPV_Marketing
            COLUMNAS_OBLIGATORIAS_ENCABEZADO = []
            COLUMNAS_OBLIGATORIAS_POR_FILA = []

        try:
            raw = uploaded_file.getvalue()

            # Intentar UTF-8
            try:
                file_content = raw.decode("utf-8")
            except UnicodeDecodeError:
                # Intentar Latin-1 (CSV estándar de Excel)
                try:
                    file_content = raw.decode("latin-1")
                except UnicodeDecodeError:
                    st.error("❌ El archivo no está en un formato válido.\n"
                            "Solo se aceptan:\n"
                            "- CSV (delimitado por comas)\n"
                            "- CSV UTF-8 (delimitado por comas)")
                    return

            lines = file_content.splitlines()

            # Detectar filas con separadores no permitidos
            #filas_con_separadores_invalidos = [
            #    idx + 1 for idx, line in enumerate(lines)
            #    if ";" in line 
            #]

            #if filas_con_separadores_invalidos:
            #    st.error(f"❌ El archivo está separado en columnas, tiene una ',' (coma) sobrante o contiene un separador no permitido (Ej.: ';') en la fila(s) {', '.join(map(str, filas_con_separadores_invalidos))}. Solo se permite el separador ',' (coma) con todos los datos en una única columna.")
            #    return

            # 1️⃣ Separador no permitido (;)
            filas_con_punto_y_coma = [
                idx + 1 for idx, line in enumerate(lines)
                if ";" in line
            ]

            if filas_con_punto_y_coma:
                st.error(
                    "❌ El archivo contiene el separador ';' (punto y coma), el cual no está permitido. Esto suele ocurrir cuando: \n\n"
                    "👉 Caso 1: El archivo importado está en formato CSV (delimitado por comas) pero en Excel se utilizó 'Texto en columnas'. El contenido del archivo debe mantenerse con todos los datos en la primera columna. \n\n"
                    "👉 Caso 2: El archivo por error de tipeo contiene ; en encabezado y/o registro. \n\n"
                    f"👉 Error en fila: {', '.join(map(str, filas_con_punto_y_coma))}\n\n"
                    "✅ Solución: \n\n"
                    "👉 Caso 1: Abrí el archivo original (con todos los datos en la primera columna) y guardalo como CSV (delimitado por comas) \n\n"
                    "👉 Caso 2: Abrí el archivo original (con todos los datos en la primera columna), realizar el cambio en la fila indicada y guardalo como CSV delimitado por comas (,) "
                )
                return


            header_line = lines[0]

            if ", " in header_line:
                columnas_con_error = [
                    col for col in header_line.split(",")
                    if col.startswith(" ")
                ]

                st.error(
                    "❌ El encabezado contiene una coma seguida de un espacio (`, `).\n\n"
                    "👉 Ejemplo inválido:\n"
                    "   User.UserId, User.UserAttributes.Nombre\n\n"
                    "👉 Ejemplo correcto:\n"
                    "   User.UserId,User.UserAttributes.Nombre\n\n"
                    "👉 Columnas afectadas:\n"
                    f"   {', '.join(col.strip() for col in columnas_con_error)}\n\n"
                    "✅ Solución: eliminá el espacio después de cada coma en el encabezado."
                )
                st.stop()
                
            header_parts = [col.strip() for col in header_line.split(separator)]
            header_parts[0] = header_parts[0].lstrip("\ufeff")

            #COLUMNAS_OBLIGATORIAS_ENCABEZADO = ["ChannelType", "Address"]

            faltantes = [
                col for col in COLUMNAS_OBLIGATORIAS_ENCABEZADO
                if col not in header_parts
            ]

            if faltantes:
                st.error(
                    "❌ El archivo es inválido.\n\n"
                    "👉 Faltan columnas obligatorias en el encabezado:\n"
                    f"   {', '.join(faltantes)}\n\n"
                    "✅ Solución: agregá estas columnas al encabezado del archivo CSV."
                )
                st.stop()
            if proyecto == "SPV_Marketing":
                if "User.UserId" not in header_parts:
                    st.error(
                        "❌ El proyecto SPV_Marketing requiere obligatoriamente la columna 'User.UserId'. \n\n"
                        "✅ Solución: agregá esta columna al encabezado del archivo CSV."
                    )
                    st.stop()
        
            if "" in header_parts:
                st.error("❌ El archivo tiene columnas sin nombre en el encabezado.\n\n"
                        "👉 Esto suele ocurrir cuando hay una coma de más en el encabezado.\n\n"
                        "✅ Solución: Borrá la coma sobrante o agregá un nombre de columna.")
                st.stop()
                error_critico = True 
            data_lines = lines[1:]

            header_cols = header_line.split(separator)
            cant_columnas_header = len(header_cols)

            filas_con_sobrantes = []
            filas_con_faltantes = []

            for numero_fila, line in enumerate(data_lines, start=2):  # fila real comienza en 2
                campos = line.split(separator)
                cant_campos = len(campos)

                if cant_campos > cant_columnas_header:
                    filas_con_sobrantes.append(numero_fila)

                if cant_campos < cant_columnas_header:
                    filas_con_faltantes.append(numero_fila)

            if filas_con_sobrantes:
                st.error(
                    "❌ Se detectaron filas con valores sobrantes (Más valores en registros que columnas en encabezado). Esto suele ocurrir cuando: \n\n"
                    "👉 Caso 1: Coma sobrante al final del registro \n\n"
                    "👉 Caso 2: Desfasaje de datos: Por cada coma detectada en el registro, será interpretado como dato de diferentes columnas, por ej.: Gutierrez, Giuliana será interpretado como Gutierrez para una columna y Giuliana para la siguiente. Esto implica un desfasaje de los datos respecto a la cantidad de columnas. \n\n"
                    f"👉 Error en fila: {', '.join(map(str, filas_con_sobrantes))}\n\n"
                    "✅ Solución: \n\n"
                    "👉 Caso 1: eliminar la coma sobrante de la fila indicada \n\n"
                    "👉 Caso 2: Reconsiderar como tratarlo debido a que Pinpoint no lo acepta. "
                )
                #st.warning(
                #    "⚠ Podés continuar bajo tu responsabilidad. "
                #    "Los datos podrían quedar desalineados."
                #)

                #if st.button("⚠ Ignorar error y continuar"):
                #    st.session_state.ignorar_sobrantes = True
                #    st.rerun()

                #st.stop()
                return

            if filas_con_faltantes:
                st.warning(
                    "⚠ Algunas filas tienen **menos valores que columnas**.\n"
                    "Los campos faltantes se interpretarán como vacíos.\n\n"
                    + f"Filas: {', '.join(map(str, filas_con_faltantes))}")

            #df = pd.read_csv(StringIO(file_content), sep=separator, engine='python', keep_default_na=False)
            df = pd.read_csv(
                StringIO(file_content),
                sep=separator,
                engine="python",
                keep_default_na=False,
                header=0,
                names=header_parts,
                #on_bad_lines="skip" if st.session_state.ignorar_sobrantes else "error"   # <--- esta es la CLAVE
            )
            df = df.reset_index(drop=True)

            #columnas_sin_nombre = [col for col in df.columns if "No tiene nombre" in col]

            prefijos_validos = ["User.UserId", "User.UserAttributes.", "Metrics.", "ChannelType", "Address"]

            column_prefix_errors = []

            for col in df.columns:
                if proyecto == "Prospectos":
                    continue

                # 👉 Para otros proyectos, validar prefijo
                if not any(col.startswith(prefijo) for prefijo in prefijos_validos):
                    column_prefix_errors.append(col)

            if column_prefix_errors:
                st.error("❌ Algunas columnas no tienen un prefijo válido. "
                        "Los prefijos permitidos (dependiendo del proyecto) son:\n"
                        "- User.UserId\n"
                        "- User.UserAttributes.NombreColumnaCamelCase \n\n"
                        "- ChannelType \n\n"
                        "- Address \n\n"
                        f"Columnas inválidas: {', '.join(column_prefix_errors)} \n\n"
                        "✅ Solución: agregá un prefijo válido a la columna")
                error_critico = True

            if error_critico:
                st.stop()

            # Si no hubo errores críticos, mostrar vista previa
            st.success("Archivo cargado correctamente ✅")
            st.subheader("📋 Vista previa del archivo:")
            st.dataframe(df.head())

        except Exception as e:
            st.error(f"Error al leer el archivo CSV: {e}")
            return

        st.subheader("🔧 Configuración de columnas:")
        column_types = {}
        column_required = {}
        #columnas_sin_nombre = [col for col in df.columns if col.strip() == "" or "sin nombre" in col.lower() or "no tiene nombre" in col.lower()]
        #COLUMNAS_OBLIGATORIAS_POR_FILA = ["Address"]
        for col in df.columns:
            col_container = st.container()
            with col_container:
                col1, col2 = st.columns([3, 1])

                if col == "User.UserId":
                    selected_type = "Entero"
                    is_required = proyecto == "SPV_Marketing"
                    col1.markdown("Tipo de dato para 'User.UserId': **Entero**")
                    if proyecto == "SPV_Marketing":
                        col2.markdown("Obligatorio: ✅")
                    else:
                        col2.markdown("Obligatorio: ❌ ")
                elif col == "ChannelType":
                    selected_type = "Texto"
                    is_required = proyecto == "Prospectos"

                    col1.markdown(
                        "Tipo de dato para 'ChannelType': **Texto**  \n"
                        "Valores permitidos: EMAIL, SMS, APNS, APNS_SANDBOX, GCM, CUSTOM"
                    )

                    col2.markdown(
                        "Obligatorio: ✅" if is_required else "Obligatorio: ❌"
                    )
                elif col in COLUMNAS_OBLIGATORIAS_POR_FILA:
                    with col1:
                        selected_type = st.selectbox(
                            f"Tipo de dato para '{col}':",
                            list(DATA_TYPES.keys()),
                            key=f"type_{col}"
                        )
                    is_required = True
                    col2.markdown("Obligatorio: ✅")
                else:
                    with col1:
                        selected_type = st.selectbox(
                            f"Tipo de dato para '{col}':",
                            list(DATA_TYPES.keys()),
                            key=f"type_{col}"
                        )
                    with col2:
                        is_required = st.checkbox(
                            "¿Es Obligatorio el campo?",
                            value=False,
                            key=f"required_{col}"
                        )

                column_types[col] = DATA_TYPES[selected_type]
                column_required[col] = is_required

        st.subheader("🔍 Resultado de la validación:")
        COLUMNAS_ENTERO_SIEMPRE_OBLIGATORIAS = ["User.UserId"]
        if st.button("▶ Validar datos"):
            with st.spinner("⏳ Validando datos, aguarde unos instantes..."):
                errors = []

                for idx, row in df.iterrows():
                    for col, expected_type in column_types.items():
                        value = row[col] if col in row else None
                        
                        required = column_required.get(col, False)
                        # 🚨 User.UserId: SIEMPRE obligatorio y SIEMPRE entero
                        if col == "User.UserId":
                            if pd.isna(value) or str(value).strip() == "":
                                errors.append({
                                    "Fila": idx + 2,
                                    "Columna": col,
                                    "Valor": value,
                                    "Error": "User.UserId es obligatorio y no puede estar vacío"
                                })
                                continue

                            try:
                                int(value)
                            except ValueError:
                                errors.append({
                                    "Fila": idx + 2,
                                    "Columna": col,
                                    "Valor": value,
                                    "Error": "User.UserId debe ser un número entero"
                                })
                                continue
                            continue
                        if col == "ChannelType" and proyecto == "Prospectos":
                            if pd.isna(value) or str(value).strip() == "":
                                errors.append({
                                    "Fila": idx + 2,
                                    "Columna": col,
                                    "Valor": value,
                                    "Error": "Campo obligatorio vacío"
                                })
                            elif str(value).strip().upper() not in CHANNEL_TYPES_VALIDOS:
                                errors.append({
                                    "Fila": idx + 2,
                                    "Columna": col,
                                    "Valor": value,
                                    "Error": (
                                        "Valor inválido. Permitidos: "
                                        "EMAIL, SMS, APNS, APNS_SANDBOX, GCM, CUSTOM"
                                    )
                                })
                            continue
                        if required and (pd.isna(value) or str(value).strip() == ""):
                            errors.append({
                                "Fila": idx + 2,
                                "Columna": col,
                                "Valor": value,
                                "Error": "Campo vacío obligatorio"
                            })
                        elif not pd.isna(value) and str(value).strip() != "" and not is_valid(value, expected_type):
                            errors.append({
                                "Fila": idx + 2,
                                "Columna": col,
                                "Valor": value,
                                "Error": f"No coincide con tipo {expected_type}"
                            })

            # El spinner desaparece acá
            if errors:
                st.error(f"Se encontraron {len(errors)} errores de datos ❌:")
                st.dataframe(pd.DataFrame(errors))
            else:
                st.success("¡Todos los datos son válidos, podés cargarlo en PinPoint! 🎉")


if __name__ == "__main__":
    main()
