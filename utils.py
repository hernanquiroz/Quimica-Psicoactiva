"""utils.py - Funciones matemáticas del simulador. UdeA."""
import numpy as np

def generar_pico_gaussiano(tiempo, altura, centro, ancho):
    return altura * np.exp(-((tiempo - centro) ** 2) / (2 * ancho ** 2))

def generar_ruido(tamano, desv_estandar, tipo="normal"):
    if tipo == "normal":
        return np.random.normal(0, desv_estandar, tamano)
    elif tipo == "1/f":
        f = np.fft.fftfreq(tamano)
        e = np.fft.fft(np.random.normal(0, desv_estandar, tamano))
        m = np.where(f != 0, 1 / np.sqrt(np.abs(f)), 0)
        return np.real(np.fft.ifft(e * m))
    raise ValueError("Use 'normal' o '1/f'.")

def calcular_lod_loq(pendiente, sigma):
    return (3.3 * sigma) / pendiente, (10.0 * sigma) / pendiente

def regresion_lineal(x, y):
    n = len(x)
    sx, sy, sxy, sx2 = np.sum(x), np.sum(y), np.sum(x * y), np.sum(x ** 2)
    m = (n * sxy - sx * sy) / (n * sx2 - sx ** 2)
    b = (sy - m * sx) / n
    yp = m * x + b
    r2 = 1 - np.sum((y - yp) ** 2) / np.sum((y - np.mean(y)) ** 2)
    return {"pendiente": m, "intercepto": b, "r_cuadrado": r2}

def cargar_datos_calibracion(ruta):
    import pandas as pd
    df = pd.read_csv(ruta)
    return df["concentracion_pM"].values, df["area_pico"].values
