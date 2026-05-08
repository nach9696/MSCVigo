from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import csv
from datetime import datetime
import os

def setup_driver():
    """Configurar Chrome en modo headless para servidor"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Modo sin interfaz gráfica
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    return webdriver.Chrome(options=chrome_options)

driver = setup_driver()
driver.maximize_window()
driver.get("https://www.msc.com/en/search-a-schedule")

wait = WebDriverWait(driver, 30)

def safe_click(element, description=""):
    """Clic seguro usando JavaScript"""
    try:
        driver.execute_script("arguments[0].click();", element)
        if description:
            print(f"✅ {description}")
        return True
    except:
        if description:
            print(f"⚠️ No se pudo hacer clic en {description}")
        return False

try:
    print("🌐 Cargando página...")
    time.sleep(5)  # Más tiempo en servidor

    # 1. ACEPTAR COOKIES
    print("🍪 Aceptando cookies...")
    try:
        cookie_btn = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//button[contains(translate(., 'ACEPTAR', 'aceptar'), 'ceptar') or contains(translate(., 'ACCEPT', 'accept'), 'ccept')]"
        )))
        safe_click(cookie_btn, "Cookies aceptadas")
        time.sleep(1)
    except:
        print("⚠️ No se encontró aviso de cookies")

    # 2. SELECCIONAR PESTAÑA
    print("🔍 Buscando pestaña 'Arrivals/Departures'...")
    xpath_tab = "//*[translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz') = 'arrivals/departures']"
    arrivals_tab = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_tab)))
    safe_click(arrivals_tab, "Pestaña Arrivals/Departures")
    time.sleep(3)

    # 3. BUSCAR CAMPO DE PUERTO
    print("🔍 Buscando campo de entrada...")
    campo_puerto = None
    for placeholder in ["Enter a port", "Port", "From", "Origen"]:
        try:
            xpath_input = f"//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{placeholder.lower()}')]"
            campo_puerto = wait.until(EC.presence_of_element_located((By.XPATH, xpath_input)))
            print(f"✅ Campo encontrado: '{placeholder}'")
            break
        except:
            continue

    if not campo_puerto:
        campo_puerto = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='text']")))

    # 4. ESCRIBIR "VIGO"
    safe_click(campo_puerto, "Campo de puerto")
    time.sleep(0.5)
    campo_puerto.clear()
    campo_puerto.send_keys("Vigo")
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", campo_puerto)
    print("✅ Escrito 'Vigo'")
    time.sleep(3)

    # 5. SELECCIONAR SUGERENCIA
    print("🖱️ Seleccionando VIGO...")
    try:
        sugerencia = wait.until(EC.element_to_be_clickable((By.XPATH,
            "//*[contains(text(), 'VIGO, SPAIN') or contains(text(), 'ESVGO')]"
        )))
        safe_click(sugerencia, "Sugerencia VIGO seleccionada")
        time.sleep(2)
    except:
        campo_puerto.send_keys(Keys.ARROW_DOWN)
        time.sleep(0.5)
        campo_puerto.send_keys(Keys.RETURN)
        print("✅ Sugerencia via teclado")
        time.sleep(2)

    # 6. PULSAR LUPA
    print("🔍 Buscando botón de búsqueda...")
    try:
        lupa = driver.find_element(By.XPATH, "//button[.//svg]")
        safe_click(lupa, "Botón de búsqueda")
    except:
        campo_puerto.send_keys(Keys.RETURN)
        print("✅ Búsqueda por Enter")
    
    time.sleep(5)

    # 7. ESPERAR RESULTADOS
    print("⏳ Esperando resultados...")
    try:
        wait.until(EC.presence_of_element_located((By.XPATH,
            "//*[contains(text(),'Vessel') or contains(text(),'Voyage')]"
        )))
        print("✅ Tabla detectada")
    except:
        print("⚠️ Timeout, pero continuando...")
    
    time.sleep(5)

    # 8. EXTRAER DATOS
    texto = driver.find_element(By.TAG_NAME, "body").text
    
    # Guardar texto completo para debug
    with open(f"debug_text_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", 'w') as f:
        f.write(texto)
    print("📝 Texto guardado para debug")

    # Parsear barcos (misma lógica que antes)
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    # Palabras a descartar
    basura = {'schedules', 'point-to-point', 'vessel', 'arrivals/departures',
              'find a schedule', 'sort by', 'arrivals', 'port', 'estimated time of arrival',
              'service', 'direct integrations solutions', 'country-location'}
    
    lineas_limpias = [l for l in lineas if l.lower() not in basura and len(l) > 2]
    
    barcos = []
    i = 0
    while i < len(lineas_limpias):
        if lineas_limpias[i] == 'Vigo':
            try:
                j = i + 1
                if j < len(lineas_limpias) and 'ESVGO' in lineas_limpias[j]:
                    j += 1
                nombre = lineas_limpias[j] if j < len(lineas_limpias) else ''
                codigo = lineas_limpias[j+1] if j+1 < len(lineas_limpias) else ''
                eta = lineas_limpias[j+2] if j+2 < len(lineas_limpias) else ''
                servicio = ''
                if j+3 < len(lineas_limpias) and lineas_limpias[j+3] != 'Vigo':
                    servicio = lineas_limpias[j+3]
                    i = j + 4
                else:
                    i = j + 3
                
                if nombre and eta:
                    barcos.append({
                        'Barco': nombre,
                        'Voyage': codigo,
                        'ETA': eta,
                        'Servicio': servicio
                    })
            except:
                i += 1
        else:
            i += 1

    # 9. MOSTRAR Y GUARDAR RESULTADOS
    print("\n" + "="*75)
    print(f"🚢 BARCOS MSC CON LLEGADA A VIGO — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("="*75)
    
    if barcos:
        for idx, b in enumerate(barcos, 1):
            print(f"{idx}. {b['Barco']} | Viaje: {b['Voyage']} | ETA: {b['ETA']} | Servicio: {b['Servicio']}")
        
        # Guardar CSV
        nombre_csv = f"vigo_msc_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        with open(nombre_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Barco','Voyage','ETA','Servicio'])
            writer.writeheader()
            writer.writerows(barcos)
        print(f"\n💾 CSV guardado: '{nombre_csv}'")
        
        # Para GitHub Actions, mostrar la ruta del archivo
        print(f"::set-output name=csv_file::{nombre_csv}")
    else:
        print("❌ No se encontraron barcos")
        # Mostrar primeras líneas del texto para debug
        print("\n📄 Primeras 20 líneas del texto extraído:")
        for idx, line in enumerate(lineas[:20], 1):
            print(f"{idx}: {line}")

    driver.save_screenshot("resultado_final_msc.png")
    print("📸 Captura guardada: 'resultado_final_msc.png'")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    driver.save_screenshot("error_critico.png")

finally:
    driver.quit()
    print("\n✅ Script finalizado")
