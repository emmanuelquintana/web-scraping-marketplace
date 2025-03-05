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
        try:
            logging.info(f"Intentando obtener información de productos para {account['name']}...")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-MX,es;q=0.8,en-US;q=0.5,en;q=0.3',
            }
            response = requests.get(account['url'], headers=headers)
            logging.info(f"Respuesta del servidor: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            products = []
            
            # Buscar todos los productos
            items = soup.find_all('div', {'class': ['ui-search-result__wrapper', 'andes-card']})
            
            logging.info(f"Productos encontrados: {len(items)}")
            
            for item in items:
                try:
                    # Buscar el título del producto
                    title_elem = item.find(['h2', 'h3'], {'class': ['ui-search-item__title', 'poly-component__title']})
                    if not title_elem:
                        title_elem = item.find('a', {'class': 'poly-component__title'})
                    
                    if title_elem:
                        title = title_elem.text.strip() if isinstance(title_elem, BeautifulSoup) else title_elem.text.strip()
                        logging.info(f"Procesando producto: {title}")
                        
                        # Buscar precios
                        original_price_elem = item.find('s', {'class': ['andes-money-amount--previous', 'price-tag-amount']})
                        current_price_elem = item.find('span', {'class': ['andes-money-amount--cents-superscript', 'price-tag-amount']})
                        
                        if original_price_elem and current_price_elem:
                            original_fraction = original_price_elem.find('span', {'class': ['andes-money-amount__fraction', 'price-tag-fraction']})
                            current_fraction = current_price_elem.find('span', {'class': ['andes-money-amount__fraction', 'price-tag-fraction']})
                            
                            if original_fraction and current_fraction:
                                original_price = original_fraction.text.strip()
                                current_price = current_fraction.text.strip()
                                
                                # Limpiar y convertir precios a números
                                try:
                                    original = float(re.sub(r'[^\d.]', '', original_price))
                                    current = float(re.sub(r'[^\d.]', '', current_price))
                                    
                                    if original > 0:  # Evitar división por cero
                                        discount = round(((original - current) / original) * 100, 2)
                                        
                                        products.append({
                                            'title': title,
                                            'discount': discount,
                                            'original_price': str(original),
                                            'current_price': str(current)
                                        })
                                        logging.info(f"Producto procesado: {title} con descuento de {discount}%")
                                except ValueError as ve:
                                    logging.error(f"Error convirtiendo precios para {title}: {str(ve)}")
                
                except Exception as e:
                    logging.error(f"Error procesando producto individual: {str(e)}")
            
            return products
        except Exception as e:
            logging.error(f"Error al obtener información: {str(e)}", exc_info=True)
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
            products = self.get_product_info(account) if account['platform'] == 'MercadoLibre' else self.get_amazon_products(account['url'])
            
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