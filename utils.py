"""
utils.py - Funciones matemáticas para el simulador cromatográfico
Práctica de Química de Sustancias Picoactivas - UdeA
Autor: [Su Nombre / Grupo de Investigación]
"""

import numpy as np
import pandas as pd

# ============================================================
# FUNCIÓN 1: Generador de Pico Cromatográfico Gaussiano
# ============================================================
def generar_pico_gaussiano(tiempo, altura, centro, ancho):
    """
    Genera un pico cromatográfico ideal usando la función gaussiana.
    
    Parámetros:
    - tiempo: array de valores de tiempo (eje X)
    - altura: altura máxima del pico (proporcional a concentración × sensibilidad)
    - centro: tiempo de retención del pico (min)
    - ancho: desviación estándar del pico (relacionado con eficiencia de columna)
    
    Retorna:
    - Array con los valores del pico en cada punto de tiempo
    """
    return altura * np.exp(-((tiempo - centro)**2) / (2 * ancho**2))


# ============================================================
# FUNCIÓN 2: Generador de Ruido Instrumental
# ============================================================
def generar_ruido(tamano, desv_estandar, tipo='normal'):
    """
    Simula el ruido del detector. Se puede elegir entre ruido blanco o ruido 1/f.
    
    Parámetros:
    - tamano: número de puntos del cromatograma
    - desv_estandar: intensidad del ruido (σ)
    - tipo: 'normal' (ruido blanco) o '1/f' (ruido rosa, más realista)
    """
    if tipo == 'normal':
        return np.random.normal(0, desv_estandar, tamano)
    elif tipo == '1/f':
        # Ruido 1/f: más realista para instrumentos reales
        frecuencias = np.fft.fftfreq(tamano)
        espectro = np.random.normal(0, desv_estandar, tamano)
        espectro_fft = np.fft.fft(espectro)
        # Atenuar altas frecuencias (1/f)
        mascara = np.where(frecuencias != 0, 1/np.sqrt(np.abs(frecuencias)), 0)
        espectro_filtrado = espectro_fft * mascara
        return np.real(np.fft.ifft(espectro_filtrado))
    else:
        raise ValueError("Tipo de ruido no reconocido. Use 'normal' o '1/f'.")


# ============================================================
# FUNCIÓN 3: Cálculo de LOD y LOQ (Norma ICH Q2)
# ============================================================
def calcular_lod_loq(pendiente, desv_estandar_respuesta):
    """
    Calcula el Límite de Detección (LOD) y Límite de Cuantificación (LOQ)
    según la metodología de la curva de calibración (ICH Q2).
    
    LOD = 3.3 × σ / S
    LOQ = 10.0 × σ / S
    
    Retorna: tupla (LOD, LOQ) en las mismas unidades de la concentración
    """
    LOD = (3.3 * desv_estandar_respuesta) / pendiente
    LOQ = (10.0 * desv_estandar_respuesta) / pendiente
    return LOD, LOQ


# ============================================================
# FUNCIÓN 4: Regresión Lineal Simple (para curva de calibración)
# ============================================================
def regresion_lineal(x, y):
    """
    Calcula pendiente, intercepto y R² de una recta y = Sx + b.
    Útil para que estudiantes validen sus curvas de calibración reales.
    """
    n = len(x)
    suma_x = np.sum(x)
    suma_y = np.sum(y)
    suma_xy = np.sum(x * y)
    suma_x2 = np.sum(x**2)
    
    pendiente = (n * suma_xy - suma_x * suma_y) / (n * suma_x2 - suma_x**2)
    intercepto = (suma_y - pendiente * suma_x) / n
    
    # Coeficiente de determinación R²
    y_pred = pendiente * x + intercepto
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r_cuadrado = 1 - (ss_res / ss_tot)
    
    return {
        'pendiente': pendiente,
        'intercepto': intercepto,
        'r_cuadrado': r_cuadrado
    }


# ============================================================
# FUNCIÓN 5: Cargar datos reales desde CSV
# ============================================================
def cargar_datos_calibracion(ruta_csv):
    """
    Carga un archivo CSV con datos reales de calibración.
    El CSV debe tener dos columnas: 'concentracion_pM' y 'area_pico'
    """
    df = pd.read_csv(ruta_csv)
    return df['concentracion_pM'].values, df['area_pico'].values
