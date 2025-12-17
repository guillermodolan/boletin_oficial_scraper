import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuración de la ruta de descargas ---
BASE_DIR = os.getcwd()
DOWNLOAD_BASE_DIR = os.path.join(BASE_DIR, "Descargas")

# Opciones de Chrome
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--log-level=3")

# Preferencias para descarga automática y sin preguntas
prefs = {
    "download.default_directory": DOWNLOAD_BASE_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True,
    "profile.default_content_settings.popups": 0
}
chrome_options.add_experimental_option("prefs", prefs)

if __name__ == "__main__":
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Usamos un 'set' porque buscar en un set es instantáneo, mucho más rápido que una lista
    urls_procesadas_historico = set()

    # Obtenemos el día actual numérico
    dia_actual_real = datetime.now().day

    print(f"--- Iniciando scraper (Hoy es día {dia_actual_real}) ---")
    url_primera_seccion = "https://www.boletinoficial.gob.ar/seccion/primera"
    driver.get(url_primera_seccion)
    # try:
    #     # Creamos este botón para ingresar a la sección "Legislación y Avisos Oficiales"
    #     btn_ingresar= WebDriverWait(driver, 10).until(
    #         EC.element_to_be_clickable((
    #             By.CSS_SELECTOR, "#layoutContent .bg-first-section a")))
    #
    #     # Mediante el click en automático, logramos ingresar
    #     btn_ingresar.click()
    # except:
    #     print("      [!] No se pudo descargar el boletin.")

    # En el siguiente bucle for recorremos el mes en curso. Está configurado para realizar 31 ciclos. Si por
    # ejemplo estamos en el mes de Junio (que tiene 30 días), mediante un break cortamos el ciclo.
    for i in range(1, 32):

        # --- FRENO DE MANO: Si el día del bucle es mayor a hoy, CORTAMOS ---
        if i > dia_actual_real:
            print(f"🛑 Deteniendo: El día {i} aún no ha ocurrido (Hoy es {dia_actual_real}).")
            break

        dia_objetivo = str(i)  # Convertimos el número a texto: "1", "2", etc.

        # ------------------- INCORPORACIÓN 1 -----------------------------------
        # Guardamos una referencia a la tabla "vieja" antes de cambiar de día
        # Esto sirve para saber cuando la tabla cambió de verdad
        try:
            tabla_vieja = driver.find_element(By.CSS_SELECTOR, ".items-section")
        except NoSuchElementException:
            tabla_vieja = None

        xpath_dia = f"//div[contains(@class, 'datepicker-days')]//td[text()='{dia_objetivo}' and not(contains(@class, 'old'))]"

        # Verificamos si el día existe ANTES de intentar esperarlo o clickearlo
        # Usamos find_elements (PLURAL) porque devuelve una lista vacía si no encuentra nada,
        # en lugar de dar error.
        coincidencias = driver.find_elements(By.XPATH, xpath_dia)

        if len(coincidencias) == 0:
            print(f"ℹ️ El día {dia_objetivo} no existe en este mes. Fin del proceso mensual.")

            # El break CORTA EL FOR que da 31 ciclos. Esto puede ocurrir si nos encontramos en Junio (como se menciona más
            # arriba).
            break
        try:
            # Esperamos a que el día sea clickeable
            elemento_dia = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, xpath_dia))
            )

            elemento_dia.click()
            print(f"✅ Click en día {dia_objetivo}")

            # [MEJORA] Espera inteligente:
            # En lugar de solo dormir 2 segundos, esperamos a que la tabla vieja desaparezca
            # o se vuelva "stale" (rancia/vieja). Esto confirma que la página está refrescando.
            if tabla_vieja:
                try:
                    WebDriverWait(driver, 5).until(EC.staleness_of(tabla_vieja))
                except:
                    # Si falla el staleness, confiamos en el sleep
                    pass

            time.sleep(3)  # Espera visual de carga

            # PASO 1. Cosechamos los links obtenidos
            links_del_dia = []
            # items = driver.find_elements(By.XPATH, "/html/body/div[4]/div/div[2]/div/div[2]/div/div[3]/div/div")
            # items = driver.find_elements(By.XPATH, "/html/body/div[4]/div/div[2]/div/div[2]/div/div[3]/div")
            items = driver.find_elements(By.CSS_SELECTOR, "#avisosSeccionDiv > div")
            print(items)

            # Creamos una lista con las palabras clave que necesitamos para buscar los artículos
            palabras_clave = ["MINISTERIO DE JUSTICIA"]

            for item in items:
                try:
                    texto_item = item.text
                    solo_titulo = texto_item.split('\n')[0]
                    if any(kw in solo_titulo for kw in palabras_clave):
                        # Extraemos el link (string) pero aún no navegamos.
                        url_link = item.find_element(By.TAG_NAME, "a").get_attribute("href")

                        # Acá aplicamos un filtro para evitar artículos duplicados.
                        if url_link not in urls_procesadas_historico:
                            links_del_dia.append(url_link)

                            # Marcamos el link como ya visto
                            urls_procesadas_historico.add(url_link)
                        else:
                            print(f"   (Saltando duplicado: {url_link[-10:]})")
                except:
                    pass

            print(f'Cantidad de links: {len(links_del_dia)}')

            if links_del_dia:
                # 1. Definimos la carpeta específica (Ej: Descargas/Dia_5)
                carpeta_destino = os.path.join(DOWNLOAD_BASE_DIR, f"Dia_{dia_objetivo}")

                # 2. Creamos la carpeta si no existe
                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)

                # 3. ### COMANDO MÁGICO ###: Cambiamos la carpeta de descarga SIN cerrar Chrome
                params = {'behavior': 'allow', 'downloadPath': carpeta_destino}
                driver.execute_cdp_cmd('Page.setDownloadBehavior', params)

                print(f"   -> Descargando en: {carpeta_destino}")

            # PASO 2. Procesamos los links encontrados
            for url_doc in links_del_dia:
                driver.get(url_doc)
                try:
                    # Guardamos el botón de descarga de un artículo que sea relevante.
                    btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "#subLayouyContentDiv .col-download button")))

                    # Clickeamos el botón mediante la línea de abajo. Esto se realiza de esta manera para evitar
                    # que se introduzcan coordenadas de posición negativas y se produzca una falla.
                    driver.execute_script("arguments[0].click();", btn)

                    print(f"      Descarga iniciada (JS Click): {url_doc}")
                    time.sleep(4)
                except Exception as e:
                    print(f'El error es: {e}')
            driver.get(url_primera_seccion)
            time.sleep(2)

        except Exception as e:
            print(f"❌ Error en día {dia_objetivo}: {e}")
            driver.get(url_primera_seccion)
        print(f"--- Procesando día: {dia_objetivo} ---")

    driver.quit()
    print("\n--- Proceso Terminado ---")