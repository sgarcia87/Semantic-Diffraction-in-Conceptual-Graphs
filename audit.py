#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Difracción v5 (refine pass) para IA_m
====================================

Novedad:
- Si el equilibrio NO es estable (ratio top1/top2 bajo), aplica un "refine pass":
  re-calcula el equilibrio usando filtro por ejes derivados del equilibrio top1 provisional (eq0).
  Esto suele eliminar contaminación (drift) cuando los polos no comparten axes.

Incluye:
- Estabilidad (ratio + balance)
- Drift suspects
- Síntesis (opcional)
- Rechazo de síntesis si top1 es polo de dualidad

Ejemplos:
  python3 test5.py --json red_fractal.json --a "viscosidad cinemática" --b "viscosidad dinámica" --sintesis --exclude_auto_dualidad --refine
  python3 test5.py --json red_fractal.json --a "número negativo" --b "signo menos" --sintesis --exclude_auto_dualidad --reject_sintesis_if_polo
"""

import json
import argparse
import networkx as nx

EXCLUIR_NODOS_DEFAULT = {
    "arriba", "abajo", "izquierda", "derecha", "delante", "detrás", "detras", "centro focal",
    "pasado", "presente", "futuro",
    "ia_m", "subconsciente", "subconsciente_semantico",
}


# -------------------------
# IO / Helpers
# -------------------------

def cargar_red(path: str) -> nx.DiGraph:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    G = nx.node_link_graph(data, edges="links")
    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    return G


def resolve_node(G: nx.DiGraph, name: str) -> str:
    if name in G:
        return name
    low = name.lower()
    for n in G.nodes():
        if str(n).lower() == low:
            return n
    return name


def tipo_nodo(G: nx.DiGraph, n: str) -> str:
    d = G.nodes.get(n, {})
    return (d.get("tipo_global") or d.get("tipo") or "concepto").lower()


def axes_de_nodo(G: nx.DiGraph, n: str) -> set:
    roles = (G.nodes.get(n, {}).get("roles") or {})
    if isinstance(roles, dict):
        return set(roles.keys())
    return set()


def normalize_axis_set(axes: set, exclude_auto_dualidad: bool) -> set:
    if not axes:
        return set()
    if not exclude_auto_dualidad:
        return set(axes)
    return {ax for ax in axes if not str(ax).startswith("eje:dualidad_auto:")}


def build_propagation_graph(G: nx.DiGraph, modo: str = "estructura", usar_pesos: bool = True) -> nx.DiGraph:
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))

    for u, v, d in G.edges(data=True):
        tipo = d.get("tipo", None)
        w = float(d.get("weight", 1.0))

        if modo == "estructura":
            if tipo == "embedding" or tipo is None:
                continue
        elif modo == "mixto":
            if tipo == "embedding":
                w = min(w, 0.2)
        elif modo == "todo":
            pass
        else:
            raise ValueError(f"modo inválido: {modo}")

        if not usar_pesos:
            w = 1.0
        else:
            w = max(0.05, min(5.0, w))

        H.add_edge(u, v, weight=w, tipo=tipo)

    return H


def ppr(H: nx.DiGraph, source: str, alpha: float = 0.85) -> dict:
    pers = {n: 0.0 for n in H.nodes()}
    pers[source] = 1.0
    return nx.pagerank(H, alpha=alpha, personalization=pers, weight="weight")


# -------------------------
# Axis selection
# -------------------------

def elegir_axes_filtro_equilibrio(G, a, b, *, axis_only=None, exclude_auto_dualidad=False):
    if axis_only:
        return {axis_only}
    axes_a = normalize_axis_set(axes_de_nodo(G, a), exclude_auto_dualidad)
    axes_b = normalize_axis_set(axes_de_nodo(G, b), exclude_auto_dualidad)
    return axes_a & axes_b


def familia_axes_desde_eq(G, a, b, eq, *, axis_only=None, exclude_auto_dualidad=False):
    """
    Construye un set de ejes útil para "refine pass" desde eq.
    Si axis_only está:
      - familia = ejes del eq que incluyan eq y a o b
      - si vacía -> axes_eq
      - si axes_eq vacío -> {axis_only}
    Si no axis_only:
      - usa axes_eq directamente (es lo más robusto)
    """
    axes_eq = normalize_axis_set(axes_de_nodo(G, eq), exclude_auto_dualidad)
    if axis_only:
        a_low = str(a).lower()
        b_low = str(b).lower()
        eq_low = str(eq).lower()
        familia = set()
        for ax in axes_eq:
            ax_low = str(ax).lower()
            if (eq_low in ax_low) and (a_low in ax_low or b_low in ax_low):
                familia.add(ax)
        if familia:
            return familia
        if axes_eq:
            return axes_eq
        return {axis_only}
    return axes_eq


def elegir_axes_filtro_sintesis(G, a, b, eq, *, axis_only=None, exclude_auto_dualidad=False):
    a_low = str(a).lower()
    b_low = str(b).lower()
    eq_low = str(eq).lower()

    axes_a = normalize_axis_set(axes_de_nodo(G, a), exclude_auto_dualidad)
    axes_b = normalize_axis_set(axes_de_nodo(G, b), exclude_auto_dualidad)
    axes_eq = normalize_axis_set(axes_de_nodo(G, eq), exclude_auto_dualidad)

    if axis_only:
        familia = set()
        for ax in axes_eq:
            ax_low = str(ax).lower()
            if (eq_low in ax_low) and (a_low in ax_low or b_low in ax_low):
                familia.add(ax)
        if familia:
            return familia
        if axes_eq:
            return axes_eq
        return {axis_only}

    axes_ab = axes_a & axes_b
    if axes_ab:
        return axes_ab
    return axes_eq if axes_eq else set()


# -------------------------
# Estabilidad y reglas
# -------------------------

def estabilidad_equilibrio(top1, top2=None, *, ratio_min=1.35, balance_max=0.80):
    razones = []
    if top1 is None:
        return False, ["sin resultados"], {}

    _, s1, pa1, pb1, *_ = top1
    denom = (pa1 + pb1)
    bal = abs(pa1 - pb1) / denom if denom > 0 else 1.0

    stats = {"score_top1": s1, "balance": bal}

    if top2 is not None:
        _, s2, *_ = top2
        stats["score_top2"] = s2
        ratio = (s1 / s2) if s2 > 0 else float("inf")
        stats["ratio"] = ratio
        if ratio < ratio_min:
            razones.append(f"ratio top1/top2 bajo ({ratio:.2f} < {ratio_min})")

    if bal > balance_max:
        razones.append(f"desbalance pa/pb alto ({bal:.2f} > {balance_max})")

    ok = (len(razones) == 0)
    return ok, razones, stats


def es_polo_de_dualidad(G, cand, *, axis_scope=None):
    cand = str(cand)
    for u, v, d in G.edges(cand, data=True):
        if d.get("tipo") == "dualidad":
            if axis_scope is None or d.get("axis") in axis_scope:
                return True
    for u, v, d in G.in_edges(cand, data=True):
        if d.get("tipo") == "dualidad":
            if axis_scope is None or d.get("axis") in axis_scope:
                return True
    return False


def diagnostico_drift(G, candidates, *, a, b, axes_filtro, exclude_auto_dualidad=False, max_show=10):
    a_axes = normalize_axis_set(axes_de_nodo(G, a), exclude_auto_dualidad)
    b_axes = normalize_axis_set(axes_de_nodo(G, b), exclude_auto_dualidad)

    sospechosos = []
    for item in candidates:
        n = item[0]
        t = tipo_nodo(G, n)
        n_axes = normalize_axis_set(axes_de_nodo(G, n), exclude_auto_dualidad)
        shared_ab = len(n_axes & (a_axes | b_axes))
        shared_filter = len(n_axes & axes_filtro) if axes_filtro else None

        if shared_ab == 0 and t not in ("equilibrio", "sintesis", "emergente"):
            sospechosos.append((n, t, shared_ab, shared_filter, sorted(list(n_axes))[:3]))

    return sospechosos[:max_show]


# -------------------------
# Difracción core
# -------------------------

def buscar_equilibrios(
    G, a, b,
    *, alpha=0.85, modo="estructura", lambda_balance=0.6,
    excluir_tipos=("emergente", "sintesis"),
    usar_filtro_axis=True, axes_filtro=None,
    exclude_auto_dualidad=False,
    top_k=40,
):
    a = resolve_node(G, a)
    b = resolve_node(G, b)

    H = build_propagation_graph(G, modo=modo, usar_pesos=True)
    if a not in H or b not in H:
        raise ValueError("Polos no aparecen en propagación. Prueba --modo mixto o --modo todo.")

    pa = ppr(H, a, alpha=alpha)
    pb = ppr(H, b, alpha=alpha)

    results = []
    for n in H.nodes():
        if n in (a, b):
            continue
        if str(n).lower() in {x.lower() for x in EXCLUIR_NODOS_DEFAULT}:
            continue
        t = tipo_nodo(G, n)
        if t in set(excluir_tipos):
            continue

        shared_axes = []
        if usar_filtro_axis and axes_filtro:
            axes_n = normalize_axis_set(axes_de_nodo(G, n), exclude_auto_dualidad)
            if not (axes_n & axes_filtro):
                continue
            shared_axes = sorted(list(axes_n & axes_filtro))

        va = float(pa.get(n, 0.0))
        vb = float(pb.get(n, 0.0))
        score = (va + vb) - lambda_balance * abs(va - vb)
        results.append((n, score, va, vb, t, shared_axes))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def buscar_sintesis(
    G, a, b, eq,
    *, alpha=0.85, modo="estructura", lambda_balance=0.5,
    usar_filtro_axis=True, axes_filtro=None,
    exclude_auto_dualidad=False,
    top_k=20,
):
    a = resolve_node(G, a)
    b = resolve_node(G, b)
    eq = resolve_node(G, eq)

    H = build_propagation_graph(G, modo=modo, usar_pesos=True)
    for x in (a, b, eq):
        if x not in H:
            raise ValueError(f"Nodo '{x}' no aparece en propagación. Prueba --modo mixto o --modo todo.")

    pa = ppr(H, a, alpha=alpha)
    pb = ppr(H, b, alpha=alpha)
    pe = ppr(H, eq, alpha=alpha)

    results = []
    for n in H.nodes():
        if n in (a, b, eq):
            continue
        if str(n).lower() in {x.lower() for x in EXCLUIR_NODOS_DEFAULT}:
            continue

        shared_axes = []
        if usar_filtro_axis and axes_filtro:
            axes_n = normalize_axis_set(axes_de_nodo(G, n), exclude_auto_dualidad)
            if not (axes_n & axes_filtro):
                continue
            shared_axes = sorted(list(axes_n & axes_filtro))

        va = float(pa.get(n, 0.0))
        vb = float(pb.get(n, 0.0))
        ve = float(pe.get(n, 0.0))
        score = (va + vb + ve) - lambda_balance * (abs(va - vb) + abs(va - ve) + abs(vb - ve))
        results.append((n, score, va, vb, ve, tipo_nodo(G, n), shared_axes))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


# -------------------------
# Main (v5)
# -------------------------

def imprimir_top_equilibrio(eq_list, top=12):
    print("⚖️ Top candidatos a EQUILIBRIO:")
    for i, (n, s, va, vb, t, shared_axes) in enumerate(eq_list[:top], 1):
        ax_info = f"  axes={shared_axes[:2]}{'…' if len(shared_axes) > 2 else ''}" if shared_axes else ""
        print(f"{i:02d}. {n:30s}  score={s:.6f}  pa={va:.6f}  pb={vb:.6f}  tipo={t}{ax_info}")


def imprimir_estabilidad(label, top1, top2, ratio_min, balance_max):
    ok, razones, stats = estabilidad_equilibrio(top1, top2, ratio_min=ratio_min, balance_max=balance_max)
    print(f"\n🧪 Estabilidad del equilibrio ({label}):")
    if ok:
        print(f"✅ ESTABLE  | balance={stats.get('balance',0):.2f}  ratio={stats.get('ratio','n/a')}")
    else:
        print(f"⚠️ NO ESTABLE | razones: {', '.join(razones)} | balance={stats.get('balance',0):.2f}  ratio={stats.get('ratio','n/a')}")
    return ok, razones, stats


def main():
    ap = argparse.ArgumentParser(description="Test difracción v5 (refine pass)")
    ap.add_argument("--json", required=True)
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--modo", default="estructura", choices=["estructura", "mixto", "todo"])
    ap.add_argument("--alpha", type=float, default=0.85)
    ap.add_argument("--lambda_balance", type=float, default=0.6)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--sintesis", action="store_true")
    ap.add_argument("--no_axis", action="store_true")
    ap.add_argument("--axis_only", default=None)
    ap.add_argument("--exclude_auto_dualidad", action="store_true")
    ap.add_argument("--ratio_min", type=float, default=1.35)
    ap.add_argument("--balance_max", type=float, default=0.80)
    ap.add_argument("--reject_sintesis_if_polo", action="store_true")
    ap.add_argument("--refine", action="store_true", help="Activa refine pass si equilibrio NO estable")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    G = cargar_red(args.json)
    a = resolve_node(G, args.a)
    b = resolve_node(G, args.b)

    usar_filtro_axis = not args.no_axis
    debug = not args.quiet

    print(f"📥 Cargado grafo: {len(G.nodes())} nodos, {len(G.edges())} aristas")
    print(f"🎯 Polos: A='{a}', B='{b}'")
    print(f"⚙️  Modo={args.modo} alpha={args.alpha} lambda_balance={args.lambda_balance}\n")

    # Pass 1: axes filtro por A∩B (o axis_only)
    axes_filtro_1 = elegir_axes_filtro_equilibrio(G, a, b, axis_only=args.axis_only, exclude_auto_dualidad=args.exclude_auto_dualidad)

    if debug:
        axes_a = normalize_axis_set(axes_de_nodo(G, a), args.exclude_auto_dualidad)
        axes_b = normalize_axis_set(axes_de_nodo(G, b), args.exclude_auto_dualidad)
        print(f"🧭 AXIS(A): {sorted(list(axes_a))[:10]}{' ...' if len(axes_a)>10 else ''}")
        print(f"🧭 AXIS(B): {sorted(list(axes_b))[:10]}{' ...' if len(axes_b)>10 else ''}")
        if args.axis_only:
            print(f"🎯 AXIS_ONLY activo: {args.axis_only}")
        print(f"🧭 AXIS filtro equilibrio (pass1): {sorted(list(axes_filtro_1))[:10]}{' ...' if len(axes_filtro_1)>10 else ''}")
        if usar_filtro_axis and axes_filtro_1:
            print("✅ Filtro AXIS activo (pass1).\n")
        elif usar_filtro_axis:
            print("⚠️ Filtro AXIS activo pero vacío (pass1): no filtra por ejes.\n")
        else:
            print("ℹ️ Filtro AXIS desactivado (pass1).\n")

    eq1 = buscar_equilibrios(
        G, a, b,
        alpha=args.alpha,
        modo=args.modo,
        lambda_balance=args.lambda_balance,
        usar_filtro_axis=usar_filtro_axis,
        axes_filtro=axes_filtro_1,
        exclude_auto_dualidad=args.exclude_auto_dualidad,
        top_k=max(40, args.top),
    )

    imprimir_top_equilibrio(eq1, top=args.top)

    top1 = eq1[0] if len(eq1) else None
    top2 = eq1[1] if len(eq1) > 1 else None
    ok1, _, _ = imprimir_estabilidad("pass1", top1, top2, args.ratio_min, args.balance_max)

    # Drift suspects pass1
    sospechosos1 = diagnostico_drift(
        G, eq1[:20], a=a, b=b, axes_filtro=axes_filtro_1, exclude_auto_dualidad=args.exclude_auto_dualidad
    )
    if sospechosos1:
        print("\n🧯 DRIFT suspects (pass1, top20):")
        for (n, t, shared_ab, shared_filter, axes_preview) in sospechosos1:
            print(f" - {n}  tipo={t}  shared_with_poles={shared_ab}  shared_with_filter={shared_filter}  axes≈{axes_preview}")

    # Refine pass
    eq_final = eq1
    axes_filtro_final = axes_filtro_1
    if args.refine and (not ok1) and top1 is not None:
        eq0 = top1[0]
        axes_filtro_2 = familia_axes_desde_eq(
            G, a, b, eq0,
            axis_only=args.axis_only,
            exclude_auto_dualidad=args.exclude_auto_dualidad
        )

        print(f"\n🧹 REFINE PASS activado: recalculando equilibrio filtrando por ejes de eq0='{eq0}'")
        if debug:
            print(f"🧭 AXIS filtro equilibrio (pass2 desde eq0): {sorted(list(axes_filtro_2))[:10]}{' ...' if len(axes_filtro_2)>10 else ''}")

        eq2 = buscar_equilibrios(
            G, a, b,
            alpha=args.alpha,
            modo=args.modo,
            lambda_balance=args.lambda_balance,
            usar_filtro_axis=True,          # en refine, forzamos filtro
            axes_filtro=axes_filtro_2,
            exclude_auto_dualidad=args.exclude_auto_dualidad,
            top_k=max(40, args.top),
        )

        print("\n⚖️ Top candidatos a EQUILIBRIO (pass2 refinado):")
        if not eq2:
            print("   (pass2 sin resultados; mantengo pass1)")
        else:
            imprimir_top_equilibrio(eq2, top=args.top)
            top1b = eq2[0] if len(eq2) else None
            top2b = eq2[1] if len(eq2) > 1 else None
            ok2, _, _ = imprimir_estabilidad("pass2", top1b, top2b, args.ratio_min, args.balance_max)

            if ok2:
                print("✅ Se adopta pass2 como resultado final.")
                eq_final = eq2
                axes_filtro_final = axes_filtro_2
            else:
                print("⚠️ pass2 no mejora suficiente; mantengo pass1.")

    # Síntesis con el equilibrio final
    if args.sintesis and eq_final:
        eq = eq_final[0][0]
        axes_filtro_s = elegir_axes_filtro_sintesis(
            G, a, b, eq,
            axis_only=args.axis_only,
            exclude_auto_dualidad=args.exclude_auto_dualidad
        )

        print(f"\n🌟 Buscando SÍNTESIS usando equilibrio final: '{eq}'")
        if debug:
            axes_eq = normalize_axis_set(axes_de_nodo(G, eq), args.exclude_auto_dualidad)
            print(f"🧭 AXIS(EQ='{eq}'): {sorted(list(axes_eq))[:10]}{' ...' if len(axes_eq)>10 else ''}")
            print(f"🧭 AXIS filtro síntesis: {sorted(list(axes_filtro_s))[:10]}{' ...' if len(axes_filtro_s)>10 else ''}")

        sints = buscar_sintesis(
            G, a, b, eq,
            alpha=args.alpha,
            modo=args.modo,
            lambda_balance=0.5,
            usar_filtro_axis=usar_filtro_axis,
            axes_filtro=axes_filtro_s,
            exclude_auto_dualidad=args.exclude_auto_dualidad,
            top_k=20,
        )

        if not sints:
            print("   (sin resultados de síntesis)")
            return

        top_s = sints[0]
        if args.reject_sintesis_if_polo:
            if es_polo_de_dualidad(G, top_s[0], axis_scope=axes_filtro_s if axes_filtro_s else None):
                print(f"🚫 Síntesis top1 '{top_s[0]}' rechazada: es polo de dualidad en ejes filtro.")
                print("🌟 Alternativas de síntesis:")
                for i, (n, s, va, vb, ve, t, shared_axes) in enumerate(sints[1:9], 1):
                    ax_info = f"  axes={shared_axes[:2]}{'…' if len(shared_axes) > 2 else ''}" if shared_axes else ""
                    print(f"{i:02d}. {n:30s}  score={s:.6f}  pa={va:.6f}  pb={vb:.6f}  pe={ve:.6f}  tipo={t}{ax_info}")
                return

        print("🌟 Top candidatos a SÍNTESIS:")
        for i, (n, s, va, vb, ve, t, shared_axes) in enumerate(sints[:10], 1):
            ax_info = f"  axes={shared_axes[:2]}{'…' if len(shared_axes) > 2 else ''}" if shared_axes else ""
            print(f"{i:02d}. {n:30s}  score={s:.6f}  pa={va:.6f}  pb={vb:.6f}  pe={ve:.6f}  tipo={t}{ax_info}")


if __name__ == "__main__":
    main()
