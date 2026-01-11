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
            return str(value).strip().lower() in ['true', 'false', 'sí', 'no']
        elif expected_type == "date":
            datetime.datetime.strptime(str(value), "%Y-%m-%d")
            return True
        elif expected_type == "email":
            return "@" in str(value)
    except:
        return False
    return False

def main():
    st.title("🧪 Validador carga de bases manuales")

    st.markdown("""
    ### ℹ️ Consideraciones importantes:
    - El archivo debe estar en formato `.csv CSV (delimitado por comas)` o `.csv CSV UTF-8 (delimitado por comas)`
    - El contenido del archivo CSV al abrir en Excel debe estar todo en la primera columna (no separado por columnas)
    - El separador correcto de columnas y campos a utilizar es **coma (`,`)**. Por cada coma detectada, será interpretada como dato de diferentes columnas, por ej.: Gutierrez, Giuliana será interpretado como Gutierrez para una columna y Giuliana para la siguiente.
    - El nombre de las columnas debe corresponder a alguno de los siguientes prefijos `User.UserId` `User.UserAttributes.NombreColumnaCamelCase`
    - Los emails pueden pertenecer a cualquier dominio
    - Las fechas deben tener el formato **AAAA-MM-DD**
    - Seleccioná el tipo de dato esperado por cada columna antes de validar
    - Si en una columna es obligatorio que exista dato, es decir no sea nulo, marcala como tal para que se detecten celdas vacías.
    """)

    uploaded_file = st.file_uploader("📂 Subí tu archivo CSV", type="csv")

    if uploaded_file is not None:
        error_critico = False
        separator = ","

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


            if header_parts[0] != "User.UserId":
                st.error(
                    "❌ El archivo es inválido.\n\n"
                    "👉 La **primera columna** debe ser obligatoriamente **User.UserId**.\n\n"
                    f"👉 Se encontró: **{header_parts[0]}**\n\n"
                    "✅ Solución: asegurá que el archivo tenga como primera columna User.UserId"
                )
                st.stop()
            if "" in header_parts:
                st.error("❌ El archivo tiene columnas sin nombre en el encabezado.\n\n"
                        "👉 Esto suele ocurrir cuando hay una coma de más al final del encabezado.\n\n"
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
                    "👉 Caso 2: Reconsiderar como tratarlo debido a que Pinpoint no lo acepta"
                )
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
                names=header_parts,   # <--- esta es la CLAVE
            )
            df = df.reset_index(drop=True)

            #columnas_sin_nombre = [col for col in df.columns if "No tiene nombre" in col]

            prefijos_validos = ["User.UserId", "User.UserAttributes.", "Metrics."]

            column_prefix_errors = []

            for col in df.columns:
                if not any(col.startswith(prefijo) for prefijo in prefijos_validos):
                    column_prefix_errors.append(col)

            if column_prefix_errors:
                st.error("❌ Algunas columnas no tienen un prefijo válido. "
                        "Los prefijos permitidos son:\n"
                        "- User.UserId\n"
                        "- User.UserAttributes.NombreColumnaCamelCase \n\n"
                        f"Columnas inválidas: {', '.join(column_prefix_errors)}")
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

        for col in df.columns:
            col_container = st.container()
            with col_container:
                col1, col2 = st.columns([3, 1])

                if col == "User.UserId":
                    selected_type = "Entero"
                    is_required = True
                    col1.markdown("Tipo de dato para 'User.UserId': **Entero**")
                    col2.markdown("Obligatorio: ✅")
                else:
                    with col1:
                        selected_type = st.selectbox(f"Tipo de dato para '{col}':", list(DATA_TYPES.keys()), key=f"type_{col}")
                    with col2:
                        is_required = st.checkbox("¿Es Obligatorio el campo?", value=True, key=f"required_{col}")

                column_types[col] = DATA_TYPES[selected_type]
                column_required[col] = is_required

        st.subheader("🔍 Resultado de la validación:")

        if st.button("▶ Validar datos"):
            with st.spinner("⏳ Validando datos, aguarde unos instantes..."):
                errors = []

                for idx, row in df.iterrows():
                    for col, expected_type in column_types.items():
                        value = row[col] if col in row else None
                        required = column_required.get(col, True)

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
