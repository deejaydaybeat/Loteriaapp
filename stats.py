"""
Estadísticas descriptivas sobre el histórico de sorteos.
IMPORTANTE: estas estadísticas describen el pasado, no predicen el futuro.
Cada sorteo es un evento independiente y equiprobable.
"""
from collections import Counter
import random
import pandas as pd


def frequency_table(df: pd.DataFrame, column: str, value_range: tuple[int, int]) -> pd.DataFrame:
    """Frecuencia de cada número (main o extra) en todo el histórico."""
    counts = Counter()
    for row in df[column]:
        counts.update(row)
    lo, hi = value_range
    data = [{"numero": n, "veces": counts.get(n, 0)} for n in range(lo, hi + 1)]
    out = pd.DataFrame(data).sort_values("numero").reset_index(drop=True)
    total_sorteos = len(df)
    out["porcentaje"] = (out["veces"] / total_sorteos * 100).round(1) if total_sorteos else 0
    return out


def atraso_table(df: pd.DataFrame, column: str, value_range: tuple[int, int]) -> pd.DataFrame:
    """
    Sorteos transcurridos desde la última vez que salió cada número
    (ordenado por fecha ascendente en df).
    """
    lo, hi = value_range
    last_seen = {n: None for n in range(lo, hi + 1)}
    total = len(df)
    for idx, row in enumerate(df[column]):
        for n in row:
            last_seen[n] = idx
    data = []
    for n in range(lo, hi + 1):
        if last_seen[n] is None:
            atraso = total  # nunca ha salido en el histórico cargado
        else:
            atraso = total - 1 - last_seen[n]
        data.append({"numero": n, "sorteos_sin_salir": atraso})
    return pd.DataFrame(data).sort_values("sorteos_sin_salir", ascending=False).reset_index(drop=True)


def top_pairs(df: pd.DataFrame, column: str, top_n: int = 15) -> pd.DataFrame:
    """Pares de números que más veces han coincidido en el mismo sorteo."""
    pair_counts = Counter()
    for row in df[column]:
        nums = sorted(row)
        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                pair_counts[(nums[i], nums[j])] += 1
    data = [{"pareja": f"{a}-{b}", "veces_juntos": c} for (a, b), c in pair_counts.items()]
    return pd.DataFrame(data).sort_values("veces_juntos", ascending=False).head(top_n).reset_index(drop=True)


def weighted_pick(freq_df: pd.DataFrame, n: int, mode: str) -> list[int]:
    """
    Genera n números sin repetición.
    mode = "caliente": pondera a favor de los más frecuentes.
    mode = "frio": pondera a favor de los menos frecuentes (mayor atraso).
    mode = "aleatorio": equiprobable, como el sorteo real.
    """
    numeros = freq_df["numero"].tolist()
    if mode == "aleatorio":
        return sorted(random.sample(numeros, n))

    pesos = freq_df["veces"].tolist()
    if mode == "frio":
        maximo = max(pesos) + 1
        pesos = [maximo - p for p in pesos]

    pesos = [p + 1 for p in pesos]  # evita peso 0
    elegidos = []
    pool = list(zip(numeros, pesos))
    for _ in range(n):
        total = sum(p for _, p in pool)
        r = random.uniform(0, total)
        acumulado = 0
        for idx, (num, peso) in enumerate(pool):
            acumulado += peso
            if acumulado >= r:
                elegidos.append(num)
                pool.pop(idx)
                break
    return sorted(elegidos)
