import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
import pywhatkit
import re
import logging

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
                # Lógica existente para Mercado Libre
                items = soup.find_all(['div', 'li'], class_=['ui-search-layout__item', 'ui-search-result'])
                logging.info(f"Encontrados {len(items)} productos en Mercado Libre")
                
                for item in items:
                    try:
                        title_elem = item.find(['h2', 'h3'], class_='ui-search-item__title')
                        title = title_elem.text.strip() if title_elem else "Sin título"
                        
                        price_elem = item.find('span', class_=['price-tag-amount', 'price-tag-fraction'])
                        current_price = float(price_elem.text.replace('$', '').replace(',', '')) if price_elem else 0
                        
                        original_price_elem = item.find('span', class_='ui-search-price__second-line')
                        original_price = current_price
                        if original_price_elem:
                            price_text = original_price_elem.find('span', class_=['price-tag-amount', 'price-tag-fraction'])
                            if price_text:
                                original_price = float(price_text.text.replace('$', '').replace(',', ''))
                        
                        url_elem = item.find('a', class_='ui-search-item__group__element')
                        product_url = url_elem['href'] if url_elem else ""
                        
                        discount = round(((original_price - current_price) / original_price) * 100) if original_price > current_price else 0
                        
                        products.append({
                            'title': title,
                            'original_price': original_price,
                            'current_price': current_price,
                            'discount': discount,
                            'url': product_url
                        })
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
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-MX,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive',
            }
            response = requests.get(url, headers=headers)
            logging.info(f"Respuesta del servidor Shein: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Determinar si es Pure and Simple o Grupo Maquilero por la URL
            is_pure_and_simple = 'store_code=7833912084' in url
            
            # Buscar productos según el tipo de tienda
            if is_pure_and_simple:
                items = soup.find_all('section', {'class': 'product-card', 'role': 'listitem'})
            else:
                items = soup.find_all('section', {'class': 'product-card'})
            
            logging.info(f"Productos encontrados: {len(items)}")
            
            for item in items:
                try:
                    # Obtener el título según el tipo de tienda
                    if is_pure_and_simple:
                        title_elem = item.find('a', {'class': 'goods-title-link'})
                        if title_elem:
                            title = title_elem.text.strip()
                            # Limpiar el título para quitar la parte de colores al final
                            if '|' in title:
                                title = title.split('|')[0].strip()
                    else:
                        title_elem = item.find('a', {'class': 'goods-title-link'})
                        if title_elem:
                            title = title_elem.text.strip()
                    
                    if title_elem:
                        # Buscar el descuento
                        discount_elem = item.find('span', {'class': 'discount-text'})
                        if discount_elem:
                            discount_text = discount_elem.text.strip()
                            discount = float(re.sub(r'[^\d.]', '', discount_text))
                            
                            # Buscar precio actual
                            current_price_elem = item.find('span', {'class': 'normal-price-ctn__sale-price'})
                            if current_price_elem:
                                price_span = current_price_elem.find('span')
                                if price_span:
                                    price_text = price_span.text.strip()
                                    # Limpiar el texto del precio (quitar MXN y espacios)
                                    current_price = re.sub(r'[^\d.]', '', price_text.replace('MXN', ''))
                                    
                                    # Convertir a números y calcular precio original
                                    try:
                                        current = float(current_price)
                                        original = round(current / (1 - discount/100), 2)
                                        
                                        products.append({
                                            'title': title,
                                            'discount': discount,
                                            'original_price': str(original),
                                            'current_price': str(current)
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
                'url': 'https://www.shein.com.mx/store/home?store_code=7833912084',
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

    