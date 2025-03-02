import ccxt
import pandas as pd
import ta
import requests
import time
from datetime import datetime
import numpy as np

# Configuración de Telegram
TELEGRAM_TOKEN = "8040415582:AAFoXlRr_gnvZcdnyEGYFrXQPZS38vowH5I"
TELEGRAM_CHAT_ID = "1122717812"

def enviar_notificacion_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        print("Notificación enviada a Telegram.")
    except requests.RequestException as e:
        print(f"Error al enviar notificación: {e}")

def obtener_indice_miedo_codicia():
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return int(data['data'][0]['value']), data['data'][0]['value_classification']
    except requests.RequestException as e:
        print(f"Error al obtener el índice de miedo y codicia: {e}")
        return None, None

def generar_informacion_mejorada(df):
    ultima_fila = df.iloc[-1]

    # MACD
    macd_tendencia = "📉 *Bajista*" if ultima_fila['macd'] < ultima_fila['macd_signal'] else "📈 *Alcista*"

    # Bollinger Bands
    if ultima_fila['close'] > ultima_fila['bollinger_high']:
        bb_ubicacion = "🔼 *Sobre la banda superior*"
    elif ultima_fila['close'] < ultima_fila['bollinger_low']:
        bb_ubicacion = "🔽 *Bajo la banda inferior*"
    else:
        bb_ubicacion = "〽️ *Dentro de las bandas*"

    # Liquidez
    liq_index = ultima_fila['liq_index']
    if liq_index > 1.2:
        estado_liq = "🔥 *Alta Liquidez*"
    elif liq_index > 0.8:
        estado_liq = "⚖️ *Liquidez Normal*"
    else:
        estado_liq = "⚠️ *Baja Liquidez*"

    # Order Flow
    delta_vol = ultima_fila['delta_volume']
    flujo = "🟢 *Compra*" if delta_vol > 0 else "🔴 *Venta*" if delta_vol < 0 else "⚪️ *Neutral*"

    return f"""
📊 **Información de la última vela (15m):**
💰 *Precio Actual:* {ultima_fila['close']:.2f}
📈 *Bollinger Bands:* {bb_ubicacion}
📉 *MACD:* {macd_tendencia}
💧 *Liquidez:* {liq_index:.2f} - {estado_liq}
📊 *Delta Volume:* {delta_vol:.2f}
🔀 *Flujo de Órdenes:* {flujo}
📊 *CVD:* {ultima_fila['cvd']:.2f}
"""

def evaluar_estrategia_mejorada(df, indice_miedo):
    ultima = df.iloc[-1]
    precio = ultima['close']
    atr = ultima['atr']
    volumen_relativo = ultima['volume'] / df['volume'].rolling(20).mean().iloc[-1]

    puntos = 0

    # 📈 **Tendencia**
    if precio > ultima['ema_200']:
        puntos += 3
    else:
        puntos -= 3

    # 🔹 **Bandas de Bollinger**
    if precio > ultima['bollinger_high'] and volumen_relativo > 1.5:
        puntos -= 4  # Sobrecompra (posible venta)
    elif precio < ultima['bollinger_low'] and volumen_relativo > 1.5:
        puntos += 4  # Sobreventa (posible compra)

    # 📊 **Volumen**
    if volumen_relativo > 1.5:
        puntos += 2
    elif volumen_relativo < 0.7:
        puntos -= 2

    # 📉 **MACD**
    macd_val = ultima['macd'] - ultima['macd_signal']
    if macd_val > 0:
        puntos += 2
    else:
        puntos -= 2

    # 📊 **Índice de Miedo y Codicia**
    if indice_miedo < 20:
        puntos += 1
    elif indice_miedo > 80:
        puntos -= 1

    # 🎯 **Generar Señal**
    if puntos >= 8:
        tp = precio + (atr * 4.5)
        sl = precio - (atr * 3.2)
        return f"""
🚀 **COMPRA**
🎯 *Take Profit:* {tp:.2f}
🛑 *Stop Loss:* {sl:.2f}
📊 *Puntuación Estrategia:* {puntos}/10
"""

    elif puntos <= -8:
        tp = precio - (atr * 4.5)
        sl = precio + (atr * 3.2)
        return f"""
🔻 **VENTA**
🎯 *Take Profit:* {tp:.2f}
🛑 *Stop Loss:* {sl:.2f}
📊 *Puntuación Estrategia:* {puntos}/10
"""

    return f"⚠️ Sin señales claras. Puntuación actual: {puntos}/10"

# Loop principal mejorado
while True:
    try:
        exchange = ccxt.kucoin()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=200)

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Indicadores principales
        df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
        df['macd'] = ta.trend.MACD(df['close']).macd()
        df['macd_signal'] = ta.trend.MACD(df['close']).macd_signal()
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['bollinger_high'] = bollinger.bollinger_hband()
        df['bollinger_low'] = bollinger.bollinger_lband()
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
        df['liq_index'] = df['volume'] / (df['volume'].rolling(96).mean() + 1e-6)
        df['delta_volume'] = df['volume'] * np.sign(df['close'].diff())
        df['cvd'] = df['delta_volume'].cumsum()

        # Obtener índice de miedo y codicia
        indice, clasificacion = obtener_indice_miedo_codicia()

        # Generar información y evaluar estrategia
        info = generar_informacion_mejorada(df)
        estrategia = evaluar_estrategia_mejorada(df, indice)

        mensaje = f"""{info}
---
🚨 **Estrategia de Trading Mejorada:**
{estrategia}
---
📊 *Índice de Miedo y Codicia:* {indice} ({clasificacion})
"""
        print(mensaje)
        enviar_notificacion_telegram(mensaje)

        time.sleep(900)  # Esperar 15 minutos entre ejecuciones

    except Exception as e:
        print(f"Error en el loop principal: {e}")
        time.sleep(300)  # Esperar 5 minutos antes de reintentar