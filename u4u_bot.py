import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
import pywhatkit
import re
import logging
import random

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('u4u_bot.log'),
        logging.StreamHandler()
    ]
)

class U4UBot:
    def __init__(self, accounts, phone_number):
        self.accounts = accounts  # Lista de diccionarios con información de las cuentas
        self.phone_number = phone_number  # Guardamos el número de teléfono
        
        self.previous_discounts = {}  # Ahora guardará los descuentos por cuenta
        logging.info(f"Bot iniciado con {len(accounts)} cuentas y número {phone_number}")

    def get_product_info(self, account):
        logging.info(f"Obteniendo información de productos para la cuenta: {account['name']}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'es-ES,es;q=0.9'
        }
        
        try:
            response = requests.get(account['url'], headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Detectar la plataforma basada en la URL
            if 'shein.com' in account['url'] or 'shein.mx' in account['url']:
                # Lógica para SHEIN
                items = soup.find_all('section', class_='product-card')
                logging.info(f"Encontrados {len(items)} productos en SHEIN")
                
                for item in items:
                    try:
                        title_elem = item.find('a', class_='goods-title-link')
                        title = title_elem.get_text().strip() if title_elem else "Sin título"
                        
                        # Obtener precio original y con descuento
                        price_wrapper = item.find('div', class_='product-card__price')
                        if price_wrapper:
                            current_price_elem = price_wrapper.find('span', class_='normal-price-ctn__sale-price')
                            current_price = current_price_elem.get_text().strip() if current_price_elem else "0"
                            
                            # Buscar el descuento
                            discount_elem = item.find('span', class_='discount-text')
                            if discount_elem:
                                discount = discount_elem.get_text().strip()
                                # Convertir el descuento de texto (ej: "-71%") a número
                                discount = int(discount.strip('-%'))
                                # Calcular el precio original
                                current_price_num = float(current_price.replace('$MXN', '').replace(',', '').strip())
                                original_price = current_price_num / (1 - discount/100)
                            else:
                                original_price = float(current_price.replace('$MXN', '').replace(',', '').strip())
                                discount = 0
                            
                            product_url = title_elem['href'] if title_elem else ""
                            if not product_url.startswith('http'):
                                product_url = f"https://www.shein.com{product_url}"
                            
                            products.append({
                                'title': title,
                                'original_price': original_price,
                                'current_price': current_price_num,
                                'discount': discount,
                                'url': product_url
                            })
                    except Exception as e:
                        logging.error(f"Error procesando producto de SHEIN: {str(e)}")
                        continue
                    
            elif 'mercadolibre' in account['url']:
                # Lógica para Mercado Libre
                items = soup.find_all(['div', 'li'], class_=['ui-search-layout__item', 'ui-search-result'])
                logging.info(f"Encontrados {len(items)} productos en Mercado Libre")
                
                for item in items:
                    try:
                        # Obtener título
                        title_elem = item.find(['h2', 'h3'], class_='ui-search-item__title')
                        title = title_elem.text.strip() if title_elem else "Sin título"
                        
                        # Buscar el contenedor de precio
                        price_container = item.find('div', class_='ui-search-price__second-line')
                        if not price_container:
                            continue
                        
                        # Obtener precio original (tachado)
                        original_price = None
                        original_price_elem = item.find('s', class_='andes-money-amount--previous')
                        if original_price_elem:
                            original_fraction = original_price_elem.find('span', class_='andes-money-amount__fraction')
                            if original_fraction:
                                original_price = float(original_fraction.text.replace(',', ''))
                        
                        # Obtener precio actual
                        current_price_elem = price_container.find('span', class_='andes-money-amount')
                        if not current_price_elem:
                            continue
                        
                        # Extraer fracción y centavos del precio actual
                        current_fraction = current_price_elem.find('span', class_='andes-money-amount__fraction')
                        current_cents = current_price_elem.find('span', class_='andes-money-amount__cents')
                        
                        if current_fraction:
                            current_price = float(current_fraction.text.replace(',', ''))
                            if current_cents:
                                current_price += float(current_cents.text) / 100
                        else:
                            continue
                        
                        # Si no hay precio original, usar el precio actual
                        if original_price is None:
                            original_price = current_price
                        
                        # Buscar descuento directamente
                        discount_elem = item.find('span', class_='andes-money-amount__discount')
                        if discount_elem:
                            discount = int(discount_elem.text.strip('%').strip('OFF').strip())
                        else:
                            # Calcular descuento solo si hay precio original y es mayor al actual
                            discount = round(((original_price - current_price) / original_price) * 100) if original_price > current_price else 0
                        
                        # Obtener URL del producto
                        url_elem = item.find('a', class_=['ui-search-item__group__element', 'ui-search-link'])
                        product_url = url_elem['href'] if url_elem else ""
                        
                        products.append({
                            'title': title,
                            'original_price': original_price,
                            'current_price': current_price,
                            'discount': discount,
                            'url': product_url
                        })
                        logging.info(f"Producto ML procesado: {title} - Precio original: ${original_price}, Precio actual: ${current_price}, Descuento: {discount}%")
                    except Exception as e:
                        logging.error(f"Error procesando producto de Mercado Libre: {str(e)}")
                        continue
                    
            elif 'amazon' in account['url']:
                # Lógica existente para Amazon
                items = soup.find_all('div', {'data-component-type': 's-search-result'})
                logging.info(f"Encontrados {len(items)} productos en Amazon")
                
                for item in items:
                    try:
                        title_elem = item.find('h2', class_='a-size-mini')
                        title = title_elem.text.strip() if title_elem else "Sin título"
                        
                        price_elem = item.find('span', class_='a-price')
                        current_price = 0
                        if price_elem:
                            price_text = price_elem.find('span', class_='a-offscreen')
                            if price_text:
                                current_price = float(price_text.text.replace('$', '').replace(',', ''))
                        
                        original_price_elem = item.find('span', class_='a-text-price')
                        original_price = current_price
                        if original_price_elem:
                            price_text = original_price_elem.find('span', class_='a-offscreen')
                            if price_text:
                                original_price = float(price_text.text.replace('$', '').replace(',', ''))
                        
                        url_elem = item.find('a', class_='a-link-normal')
                        product_url = f"https://www.amazon.com.mx{url_elem['href']}" if url_elem else ""
                        
                        discount = round(((original_price - current_price) / original_price) * 100) if original_price > current_price else 0
                        
                        products.append({
                            'title': title,
                            'original_price': original_price,
                            'current_price': current_price,
                            'discount': discount,
                            'url': product_url
                        })
                    except Exception as e:
                        logging.error(f"Error procesando producto de Amazon: {str(e)}")
                        continue
            
            logging.info(f"Total de productos encontrados: {len(products)}")
            return products
            
        except Exception as e:
            logging.error(f"Error al obtener productos: {str(e)}")
            return []

    def get_amazon_products(self, url):
        try:
            logging.info("Intentando obtener información de productos de Amazon...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-MX,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive',
            }
            response = requests.get(url, headers=headers)
            logging.info(f"Respuesta del servidor Amazon: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            

            
            # Buscar productos de Amazon
            items = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            for item in items:
                try:
                    # Verificar si es un producto U4U Uniforms
                    brand_element = item.find('span', string=lambda text: text and "U4U Uniforms" in text)
                    if brand_element:
                        # Obtener el título
                        title_element = item.find('h2', {'class': 'a-size-mini'})
                        if title_element:
                            title = title_element.get_text().strip()
                            
                            
                            # Buscar precio con descuento (precio actual)
                            current_price_elem = item.find('span', {'class': 'a-price'})
                            # Buscar precio original (precio de lista)
                            original_price_elem = item.find('span', {'class': 'a-price a-text-price'})
                            
                            if original_price_elem and current_price_elem:
                                # Extraer precios
                                original_price = original_price_elem.find('span', {'class': 'a-offscreen'}).text
                                current_price = current_price_elem.find('span', {'class': 'a-offscreen'}).text
                                
                                # Limpiar y convertir precios a números
                                original = float(re.sub(r'[^\d.]', '', original_price))
                                current = float(re.sub(r'[^\d.]', '', current_price))
                                
                                # Calcular descuento
                                if original > 0:  # Evitar división por cero
                                    discount = round(((original - current) / original) * 100, 2)
                                    
                                    products.append({
                                        'title': title,
                                        'discount': discount,
                                        'original_price': str(original),
                                        'current_price': str(current),
                                        'platform': 'Amazon'
                                    })
                                    logging.info(f"Producto Amazon encontrado: {title} con descuento de {discount}%")
                
                except Exception as e:
                    logging.error(f"Error procesando producto Amazon individual: {str(e)}")
            
            logging.info(f"Total de productos U4U encontrados en Amazon: {len(products)}")
            return products
        except Exception as e:
            logging.error(f"Error al obtener información de Amazon: {str(e)}", exc_info=True)
            return []

    def get_shein_products(self, url):
        try:
            logging.info("Intentando obtener información de productos de Shein...")
            
            session = requests.Session()
            
            # Headers actualizados basados en el curl proporcionado
            headers = {
                'authority': 'www.shein.com.mx',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'es-419,es;q=0.9,es-ES;q=0.8,en;q=0.7,en-GB;q=0.6,en-US;q=0.5,es-MX;q=0.4,sl;q=0.3',
                'cache-control': 'max-age=0',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Microsoft Edge";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0'
            }
            
            # Cookies actualizadas basadas en el curl
            cookies = {
                'cookieId': '65D591C9_8E28_D9E4_21D3_AB1396E19BC3',
                'RESOURCE_ADAPT_WEBP': '1',
                'smidV2': '2024081200523803b29cbcbfd28f8787703bd5bcd74e3700f971a5b1da6bd10',
                '_aimtellSubscriberID': '34ec7bca-c590-536b-cf92-8528deb74e25',
                'fita.sid.shein': 'TTDHdVwE0PJK4FsO5cQXGN-KWDFZEYU7',
                '_pin_unauth': 'dWlkPU1HUTBaVGxoTXpFdE9USmpZUzAwTXpabUxUazRPVE10TlRRMU9UTmpaRE01Wm1Jeg',
                'armorUuid': '202408120052383c1f5b816fb3ed3f47d0a2591ab56908009ef7ceb5933c4800',
                'g_state': '{"i_l":0}',
                'webpushcookie': 'agree:1',
                '_gcl_au': '1.1.1785415289.1740156478',
                '_csrf': 'tcv_nHFi0lgxMd0p7WCt_2bI',
                'forterToken': 'ffe68ff2c01a48f78ecc000c68e39c23_1741151849033__UDF43-m4_17ck_',
                '_rdt_uuid': '1723445562704.4b10a7a6-66da-4da9-a499-de9a87e2214b',
                'memberId': '4724834900',
                'sessionID_shein': 's:LtdVwJVm7xywC64JhYpW7wFb_iJbI_Mq.Jh81QuArzI2p08EMr/L+VbiBZ2bQMuoIrfXHFN5mEwM'
            }
            
            # Si es Pure and Simple, simplificar la URL
            if 'store_code=7833912084' in url:
                url = 'https://www.shein.com.mx/store/home?store_code=7833912084&tab=items'
            
            # Hacer la petición principal
            logging.info(f"Realizando petición a URL: {url}")
            response = session.get(url, headers=headers, cookies=cookies)
            logging.info(f"Respuesta del servidor Shein: {response.status_code}")
            
            # Guardar HTML para debugging
            with open('debug_shein.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Determinar si es Pure and Simple o Grupo Maquilero
            is_pure_and_simple = 'store_code=7833912084' in url
            
            if is_pure_and_simple:
                # Intentar diferentes selectores para Pure and Simple
                items = []
                selectors = [
                    {'class': 'product-card multiple-row-card j-expose__product-item'},
                    {'class': 'product-card multiple-row-card'},
                    {'class': 'j-expose__product-item'},
                    {'class': 'S-product-item j-expose__product-item'},
                    {'class': 'product-card', 'role': 'listitem'}
                ]
                
                for selector in selectors:
                    items = soup.find_all(['div', 'section'], selector)
                    if items:
                        logging.info(f"Pure and Simple - Productos encontrados con selector {selector}: {len(items)}")
                        break
                
                if not items:
                    # Intentar buscar por el contenedor principal
                    container = soup.find('div', {'class': 'product-list__items'})
                    if container:
                        items = container.find_all(['div', 'section'], {'class': lambda x: x and 'product-card' in x})
                        logging.info(f"Pure and Simple - Productos encontrados en contenedor principal: {len(items)}")
            else:
                items = soup.find_all('section', {'class': 'product-card'})
                logging.info(f"Grupo Maquilero - Productos encontrados: {len(items)}")
            
            for item in items:
                try:
                    if is_pure_and_simple:
                        # Buscar título en múltiples lugares
                        title_elem = (
                            item.find('a', {'class': ['goods-title-link--jump', 'S-product-card__img-container']}) or
                            item.find('a', {'aria-label': True}) or
                            item.find('a', {'class': lambda x: x and 'goods-title-link' in x})
                        )
                        
                        # Buscar descuento en múltiples lugares
                        discount_elem = (
                            item.find('div', {'class': 'discount-label'}) or
                            item.find('span', {'class': 'discount-text'})
                        )
                        
                        # Buscar precio en múltiples lugares
                        price_wrapper = (
                            item.find('div', {'class': ['product-card__price', 'product-card__prices-info']}) or
                            item.find('div', {'class': lambda x: x and 'price' in x.lower()})
                        )
                    else:
                        # Selectores para Grupo Maquilero (sin cambios)
                        title_elem = item.find('a', {'class': 'goods-title-link'})
                        discount_elem = item.find('span', {'class': 'discount-text'})
                        price_wrapper = item.find('div', {'class': 'product-card__price'})

                    if title_elem:
                        # Obtener título
                        title = title_elem.get('aria-label', '') or title_elem.text.strip()
                        if '|' in title:
                            title = title.split('|')[0].strip()
                        
                        # Obtener descuento
                        discount = 0
                        if discount_elem:
                            discount_text = ''
                            if is_pure_and_simple:
                                discount_span = discount_elem.find('span', {'class': 'discount-text'})
                                if discount_span:
                                    discount_text = discount_span.text.strip()
                                else:
                                    discount_text = discount_elem.text.strip()
                            else:
                                discount_text = discount_elem.text.strip()
                            
                            if discount_text:
                                try:
                                    discount = float(re.sub(r'[^\d.]', '', discount_text))
                                except ValueError:
                                    logging.error(f"Error convirtiendo descuento: {discount_text}")
                        
                        # Obtener precios
                        if price_wrapper:
                            current_price_elem = (
                                price_wrapper.find('span', {'class': ['normal-price-ctn__sale-price', 'normal-price-ctn__sale-price_promo']}) or
                                price_wrapper.find('p', {'class': 'product-item__camecase-wrap'})
                            )
                            
                            if current_price_elem:
                                price_text = current_price_elem.text.strip()
                                current_price = re.sub(r'[^\d.]', '', price_text.replace('MXN', ''))
                                
                                try:
                                    current = float(current_price)
                                    original = round(current / (1 - discount/100), 2) if discount > 0 else current
                                    
                                    # Obtener URL del producto
                                    product_url = title_elem.get('href', '')
                                    if not product_url.startswith('http'):
                                        product_url = f"https://www.shein.com.mx{product_url}"
                                    
                                    products.append({
                                        'title': title,
                                        'discount': discount,
                                        'original_price': str(original),
                                        'current_price': str(current),
                                        'url': product_url
                                    })
                                    logging.info(f"Producto Shein encontrado: {title} con descuento de {discount}%")
                                except ValueError as ve:
                                    logging.error(f"Error convirtiendo precios para {title}: {str(ve)}")
                
                except Exception as e:
                    logging.error(f"Error procesando producto Shein individual: {str(e)}")
            
            logging.info(f"Total de productos encontrados en Shein: {len(products)}")
            return products
            
        except Exception as e:
            logging.error(f"Error al obtener información de Shein: {str(e)}", exc_info=True)
            return []

    def send_whatsapp_message(self, message):
        try:
            logging.info("Intentando enviar mensaje consolidado")
            clean_number = self.phone_number.replace('+52 1 ', '')
            
            # Asegurarnos que el mensaje no esté vacío
            if not message.strip():
                logging.warning("Mensaje vacío, no se enviará")
                return
            
                
            # Enviar mensaje por WhatsApp
            pywhatkit.sendwhatmsg_instantly(
                f"+521{clean_number}",
                message,
                10,  # Tiempo de espera reducido
                tab_close=False  # No cerrar la pestaña para asegurar el envío
            )
            logging.info("Mensaje enviado exitosamente")
            time.sleep(5)  # Pequeña pausa después de enviar
        except Exception as e:
            logging.error(f"Error al enviar mensaje: {str(e)}", exc_info=True)

    def check_discounts(self):
        logging.info("Iniciando verificación de descuentos...")
        all_messages = []
        urgent_messages = []
        first_run = not bool(self.previous_discounts)  # Verificar si es la primera ejecución
        
        # Verificar productos
        for account in self.accounts:
            if account['platform'] == 'MercadoLibre':
                products = self.get_product_info(account)
            elif account['platform'] == 'Amazon':
                products = self.get_amazon_products(account['url'])
            else:  # Shein
                products = self.get_shein_products(account['url'])
            
            if not products:
                logging.warning(f"No se encontraron productos para {account['name']}")
                continue
            
            message_parts = [f"🏪 {account['name'].upper()} ({account['platform']})\n{'='*30}\n"]
            changes_detected = False
            
            account_key = account['name']
            if account_key not in self.previous_discounts:
                self.previous_discounts[account_key] = {}
            
            for product in products:
                current_discount = product['discount']
                previous_discount = self.previous_discounts[account_key].get(product['title'], None)
                
                # Mensaje base del producto
                product_info = (
                    f"\n📦 Producto: {product['title']}\n"
                    f"💰 Precio original: ${product['original_price']}\n"
                    f"🏷️ Precio actual: ${product['current_price']}\n"
                    f"📊 Descuento: {current_discount}%\n"
                )
                
                # Verificar si el producto perdió su descuento
                if previous_discount is not None and previous_discount > 0 and current_discount == 0:
                    urgent_message = (
                        f"\n{'🚨'*5} ¡ALERTA URGENTE! {'🚨'*5}\n"
                        f"{'='*40}\n"
                        f"❌ PRODUCTO SIN DESCUENTO ❌\n"
                        f"📦 Producto: {product['title']}\n"
                        f"💰 Precio actual: ${product['current_price']}\n"
                        f"⚠️ ¡ACCIÓN INMEDIATA REQUERIDA!\n"
                        f"{'='*40}\n"
                    )
                    urgent_messages.append(urgent_message)
                
                # Agregar al reporte regular
                if current_discount == 0:
                    product_info = (
                        f"\n⚠️ PRODUCTO SIN DESCUENTO\n"
                        f"📦 Producto: {product['title']}\n"
                        f"💰 Precio: ${product['original_price']}\n"
                    )
                    changes_detected = True
                elif previous_discount is None:
                    product_info += "✨ (Nuevo producto)\n"
                    changes_detected = True
                elif current_discount != previous_discount:
                    if current_discount < previous_discount:
                        product_info += f"📉 Descuento REDUCIDO: {previous_discount}% → {current_discount}%\n"
                    else:
                        product_info += f"📈 Descuento AUMENTADO: {previous_discount}% → {current_discount}%\n"
                    changes_detected = True
                
                message_parts.append(product_info)
                self.previous_discounts[account_key][product['title']] = current_discount
            
            if changes_detected or first_run:
                message = "".join(message_parts)
                all_messages.append(message)
        
        # Enviar mensajes urgentes inmediatamente (productos sin descuento)
        if urgent_messages:
            urgent_final = "🚨 ¡ALERTAS URGENTES! 🚨\n\n" + "\n\n".join(urgent_messages)
            urgent_final += f"\n\n⏰ Alerta generada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.send_whatsapp_message(urgent_final)
        
        # Enviar reporte completo en primera ejecución o en horarios programados
        current_hour = datetime.now().hour
        if first_run or current_hour in [9, 18]:  # Primera ejecución o 9 AM/6 PM
            if all_messages:
                header = "📊 REPORTE INICIAL DE PRODUCTOS 📊\n\n" if first_run else "📊 REPORTE PROGRAMADO 📊\n\n"
                final_message = header + "\n\n".join(all_messages)
                final_message += f"\n\n⏰ Reporte generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                self.send_whatsapp_message(final_message)
            else:
                logging.info("No hay cambios para reportar")

def main():
    try:
        logging.info("Iniciando el bot...")
        
        # Configuración de las cuentas
        accounts = [
            {
                'name': 'Marcas y Licencias Godlval',
                'url': 'https://listado.mercadolibre.com.mx/_CustId_366058927?item_id=MLM774983214&category_id=MLM437528&seller_id=366058927&client=recoview-selleritems&recos_listing=true#origin=vip&component=sellerData&typeSeller=classic',
                'type': 'normal',
                'platform': 'MercadoLibre'
            },
            {
                'name': 'Grupo Maquilero',
                'url': 'https://listado.mercadolibre.com.mx/tienda/u4u/',
                'type': 'official',
                'platform': 'MercadoLibre'
            },
            {
                'name': 'U4U Amazon Store',
                'url': 'https://www.amazon.com.mx/s?k=u4u+uniformes&crid=7HLPL67JZQDM&sprefix=U4U+UNIFOEM%2Caps%2C131&ref=nb_sb_ss_mvt-t9-ranker_1_11',
                'platform': 'Amazon'
            },
            {
                'name': 'U4U Shein Grupo Maquilero',
                'url': 'https://www.shein.com.mx/Brands/U4U-Uniforms-sc-0141887884.html',
                'platform': 'Shein'
            },
            
            {
                'name': 'U4U Shein Pure and Simple',
                'url': 'https://www.shein.com.mx/store/home?store_code=7833912084&type=selection&routeId=1022271124&ici=PageGoodsDetail&main_cate_id=1980&main_goods_id=58618356&rule_poskey=DetailShopItemList&src_identifier=on=store`cn=U4U%20Uniforms`hz=0`ps=1_1`jc=thirdPartyStoreHome_7833912084&src_module=DetailBrand&src_tab_page_id=page_goods_detail1741152307333&tab=items',
                'platform': 'Shein'
            }
        ]
        
        phone_number = "+52 1 55 1836 1539"
        bot = U4UBot(accounts, phone_number)
        
        # Primera verificación inmediata
        logging.info("Ejecutando primera verificación...")
        bot.check_discounts()
        
        # Programar la verificación cada hora
        schedule.every(1).hours.do(bot.check_discounts)
        logging.info("Verificación programada cada hora")
        
        # Mantener el bot ejecutándose
        logging.info("Bot en ejecución...")
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        logging.error(f"Error en la función principal: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 

    
    