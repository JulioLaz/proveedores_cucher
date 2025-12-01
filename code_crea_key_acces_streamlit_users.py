"""
Script para generar configuración de autenticación
SOLO MUESTRA - No sobrescribe secrets.toml existente
"""

import pandas as pd
import streamlit_authenticator as stauth
from datetime import datetime
import time

# ══════════════════════════════════════════════════════════════
# INICIO DE EJECUCIÓN
# ══════════════════════════════════════════════════════════════
inicio = time.time()
print("\n" + "="*70)
print("🔐 GENERADOR DE CONFIGURACIÓN DE AUTENTICACIÓN")
print("="*70)

# Leer CSV de usuarios
usuarios_df = pd.read_csv(r'C:\JulioPrograma\CUCHER-MERCADOS\cuchermercados-main\cuchermercados-main\presupuesto\codigos\all\PRESUPUESTO_FEB_2025\TICKETS_2024_2025_ALL\presupuesto\destinatarios_email_cucher.csv')
usuarios_df['email'] = usuarios_df['email'].str.strip()
usuarios_df['nombre'] = usuarios_df['nombre'].str.strip()

print(f"\n📊 Usuarios encontrados: {len(usuarios_df)}")

# Generar credenciales
credentials = {'usernames': {}}

print("\n" + "-"*70)
print("GENERANDO CREDENCIALES")
print("-"*70)

for idx, row in usuarios_df.iterrows():
    username = row['email'].split('@')[0]
    nombre = row['nombre']
    password_temp = f"{nombre[:3].lower()}2025"
    # hashed_password = stauth.Hasher([password_temp]).generate()[0]
    hashed_password = stauth.Hasher.hash(password_temp)
    credentials['usernames'][username] = {
        'name': nombre,
        'password': hashed_password,
        'email': row['email']
    }
    
    print(f"✓ {nombre:20} | user: {username:30} | pass: {password_temp}")

# ══════════════════════════════════════════════════════════════
# GENERAR CONTENIDO PARA AGREGAR
# ══════════════════════════════════════════════════════════════

contenido_agregar = f'''
# ═══════════════════════════════════════════════════════════════
# AUTENTICACIÓN - Agregado el {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# ═══════════════════════════════════════════════════════════════

[credentials]
'''

for username, data in credentials['usernames'].items():
    contenido_agregar += f'''
[credentials.usernames.{username}]
name = "{data['name']}"
password = "{data['password']}"
email = "{data['email']}"
'''

contenido_agregar += '''
[cookie]
name = "cucher_dashboard"
key = "cucher_secret_key_2025_dashboard"
expiry_days = 30
'''

# Guardar en archivo separado
with open('auth_config_para_agregar.txt', 'w', encoding='utf-8') as f:
    f.write(contenido_agregar)

# ══════════════════════════════════════════════════════════════
# MOSTRAR EN TERMINAL
# ══════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("📋 COPIA Y PEGA ESTO AL FINAL DE TU secrets.toml")
print("="*70)
print(contenido_agregar)
print("="*70)

# ══════════════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════════════
tiempo_total = time.time() - inicio

print(f"\n📄 INSTRUCCIONES:")
print(f"   1. Abre: .streamlit/secrets.toml")
print(f"   2. Ve al FINAL del archivo")
print(f"   3. Pega el contenido mostrado arriba")
print(f"   4. Guarda el archivo")
print(f"\n   También guardé el contenido en: auth_config_para_agregar.txt")

print(f"\n⚠️  RECUERDA:")
print(f"   • Contraseñas temporales: [nombre]2025")
print(f"   • NO subir secrets.toml a GitHub")
print(f"   • El archivo secrets.toml se recarga automáticamente")

print(f"\n⏱️  Tiempo de ejecución: {tiempo_total:.3f} segundos")
print("="*70 + "\n")