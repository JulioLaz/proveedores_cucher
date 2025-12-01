import requests
from datetime import datetime
import streamlit as st
import pytz

def send_telegram_notification(username, name, email, success=True):
    """
    Envía notificación a Telegram cuando un usuario inicia sesión
    
    Args:
        username: Usuario que inició sesión
        name: Nombre completo del usuario
        email: Email del usuario
        success: Si el login fue exitoso o falló
    """
    try:
        # Obtener credenciales de Telegram desde secrets
        telegram_token = st.secrets.get('telegram', {}).get('bot_token')
        telegram_chat_id = st.secrets.get('telegram', {}).get('chat_id')
        
        if not telegram_token or not telegram_chat_id:
            print("⚠️  [TELEGRAM] Credenciales no configuradas - Notificación omitida")
            return False
        
        # ✅ HORA DE ARGENTINA (GMT-3)
        tz_argentina = pytz.timezone('America/Argentina/Cordoba')
        timestamp = datetime.now(tz_argentina).strftime('%d/%m/%Y %H:%M:%S')
        
        if success:
            emoji = "✅"
            action = "ACCESO EXITOSO"
        else:
            emoji = "❌"
            action = "INTENTO FALLIDO"
        
        mensaje = f"""
{emoji} <b>{action} - Dashboard Proveedores</b>

👤 <b>Usuario:</b> {username}
📝 <b>Nombre:</b> {name}
📧 <b>Email:</b> {email}
🕒 <b>Fecha/Hora:</b> {timestamp} (ARG)
🖥️ <b>App:</b> Análisis de Proveedores Cucher
"""
        
        # Enviar mensaje
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            'chat_id': telegram_chat_id,
            'text': mensaje,
            'parse_mode': 'HTML'
        }
        
        print(f"\n📤 [TELEGRAM] Enviando notificación de acceso...")
        print(f"   👤 Usuario: {username} ({name})")
        print(f"   🕒 Timestamp: {timestamp} (ARG)")
        
        response = requests.post(url, data=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"✅ [TELEGRAM] Notificación enviada exitosamente")
            return True
        else:
            print(f"❌ [TELEGRAM] Error al enviar: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ [TELEGRAM] Error inesperado: {str(e)}")
        return False


def send_telegram_alert(mensaje, tipo="INFO"):
    """
    Envía alerta genérica a Telegram
    
    Args:
        mensaje: Texto del mensaje
        tipo: INFO, WARNING, ERROR, SUCCESS
    """
    try:
        telegram_token = st.secrets.get('telegram', {}).get('bot_token')
        telegram_chat_id = st.secrets.get('telegram', {}).get('chat_id')
        
        if not telegram_token or not telegram_chat_id:
            return False
        
        # Emojis según tipo
        emojis = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'SUCCESS': '✅'
        }
        
        emoji = emojis.get(tipo, 'ℹ️')
        
        # ✅ HORA DE ARGENTINA
        tz_argentina = pytz.timezone('America/Argentina/Cordoba')
        timestamp = datetime.now(tz_argentina).strftime('%d/%m/%Y %H:%M:%S')
        
        mensaje_formatted = f"""
{emoji} <b>{tipo}</b>

{mensaje}

🕒 {timestamp} (ARG)
"""
        
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            'chat_id': telegram_chat_id,
            'text': mensaje_formatted,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=payload, timeout=5)
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ [TELEGRAM] Error en alerta: {str(e)}")
        return False