import io
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from ga_solver import load_excel, run_ga, brute_force

st.set_page_config(page_title="GA Warehouse Optimizer", page_icon="🧬", layout="wide")
st.markdown("""
<style>
.hero{background:linear-gradient(135deg,#0f2742,#1f6f8b 60%,#2ec4b6);padding:2.2rem 2.5rem;border-radius:18px;color:#fff;margin-bottom:1.2rem}
.hero h1{margin:0;font-size:2.3rem;color:#fff}.hero p{margin:.4rem 0 0;font-size:1.05rem;opacity:.92}
.chip{display:inline-block;background:rgba(255,255,255,.18);border-radius:20px;padding:.2rem .8rem;margin:.8rem .4rem 0 0;font-size:.85rem}
.kpi{background:#fff;border:1px solid #e3e8ef;border-left:5px solid #2ec4b6;border-radius:12px;padding:1rem 1.2rem}
.kpi b{display:block;font-size:1.6rem;color:#0f2742}.kpi span{color:#5b6b7f;font-size:.85rem}
.step{background:#f5f8fb;border-radius:12px;padding:1rem 1.2rem;height:100%;color:#0f2742}
</style>
<div class="hero"><h1>🧬 Warehouse Network Optimizer</h1>
<p>Decide which warehouses to open and how to route goods, minimising upstream + downstream transport and fixed opening costs, using a <b>Genetic Algorithm</b>.</p>
<span class="chip">Evolutionary optimisation</span><span class="chip">Two-echelon network</span><span class="chip">Capacitated MILP</span></div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("1 · Data")
    up = st.file_uploader("Upload input Excel", type="xlsx")
    try:
        with open("input_template.xlsx", "rb") as f:
            st.download_button("⬇️ Download Excel template", f.read(), "input_template.xlsx")
    except FileNotFoundError:
        st.caption("Run make_template.py to create the template.")
    st.header("2 · Genetic algorithm")
    pop = st.slider("Population size", 10, 200, 30, 5)
    gens = st.slider("Generations", 5, 300, 40, 5)
    pcx = st.slider("Crossover probability", 0.0, 1.0, 0.85, 0.05)
    pmut = st.slider("Mutation probability (per bit)", 0.0, 0.5, 0.08, 0.01)
    tour = st.slider("Tournament size", 2, 8, 3)
    elite = st.slider("Elitism (survivors)", 0, 10, 2)
    seed = st.number_input("Random seed", 0, 99999, 42)
    verify = st.checkbox("Verify with exhaustive search (≤ 12 warehouses)", True)

tab_solve, tab_how = st.tabs(["🚀 Solve", "📘 How the genetic algorithm works"])

with tab_how:
    c = st.columns(4)
    for col, (t, txt) in zip(c, [
        ("1 · Encode", "Each individual is a binary string: bit *i* = 1 means warehouse *i* is open."),
        ("2 · Evaluate", "Fitness = fixed costs + the cheapest transport plan for that open set (solved by a small LP)."),
        ("3 · Select & recombine", "Tournament selection picks parents; uniform crossover mixes them; mutation flips bits."),
        ("4 · Repair & evolve", "Capacity-infeasible children are repaired; elitism keeps the best. Repeat for N generations.")]):
        col.markdown(f'<div class="step"><b>{t}</b><br>{txt}</div>', unsafe_allow_html=True)
    st.markdown("**Model:** min Σ Fᵢyᵢ + Σ Cₖᵢxₖᵢ + Σ Dᵢⱼzᵢⱼ  s.t. demand, supply, flow conservation and capacity (Σⱼ zᵢⱼ ≤ Capᵢ·yᵢ).")

with tab_solve:
    src = up if up is not None else ("input_template.xlsx" if st.session_state.get("demo") else None)
    if up is None:
        if st.button("Try with the example data"):
            st.session_state["demo"] = True; st.rerun()
        src = "input_template.xlsx" if st.session_state.get("demo") else None
    if src is None:
        st.info("Upload your Excel file in the sidebar (or use the example data) to begin.")
        st.stop()
    try:
        d = load_excel(src)
    except Exception as e:
        st.error(f"Could not read the file: {e}"); st.stop()
    K, I, J = len(d.O), len(d.F), len(d.R)
    m = st.columns(4)
    for col, (v, l) in zip(m, [(K, "Suppliers"), (I, "Candidate warehouses"), (J, "Customers"),
                               (f"{d.R.sum():,.0f}", "Total demand")]):
        col.markdown(f'<div class="kpi"><b>{v}</b><span>{l}</span></div>', unsafe_allow_html=True)
    with st.expander("Preview input data"):
        st.dataframe(pd.DataFrame({"Warehouse": d.wh_names, "Fixed cost": d.F, "Capacity": d.Cap}), hide_index=True)

    if st.button("🧬 Run genetic algorithm", type="primary", use_container_width=True):
        bar, live = st.progress(0.0), st.empty()
        def cb(p, h):
            bar.progress(min(p, 1.0)); live.caption(f"Generation {h['generation']} · best cost {h['best']:,.0f}")
        st.session_state["res"] = run_ga(d, pop, gens, pcx, pmut, tour, elite, int(seed), cb)
        st.session_state["opt"] = brute_force(d) if verify and I <= 12 else None
        live.empty(); bar.empty()

    r = st.session_state.get("res")
    if r is not None and len(r["y"]) == I:
        st.subheader("Optimal solution found")
        k = st.columns(5)
        for col, (v, l) in zip(k, [(f"{r['total']:,.0f}", "Total cost"), (f"{r['fixed']:,.0f}", "Fixed costs"),
                                   (f"{r['upstream']:,.0f}", "Upstream transport"),
                                   (f"{r['downstream']:,.0f}", "Downstream transport"),
                                   (f"{int(r['y'].sum())} / {I}", "Warehouses opened")]):
            col.markdown(f'<div class="kpi"><b>{v}</b><span>{l}</span></div>', unsafe_allow_html=True)
        opt = st.session_state.get("opt")
        if opt:
            gap = (r["total"] - opt) / opt * 100
            st.success(f"Exhaustive search optimum: {opt:,.0f} → GA gap **{gap:.2f}%**")
        st.caption(f"{r['evaluations']} distinct solutions evaluated in {r['seconds']:.2f}s "
                   f"(search space: {2**I} open-sets).")

        h = r["history"]
        fig = go.Figure()
        fig.add_scatter(x=h.generation, y=h.worst, name="Worst", line=dict(color="#c9d3df", dash="dot"))
        fig.add_scatter(x=h.generation, y=h["mean"], name="Population mean", line=dict(color="#1f6f8b"))
        fig.add_scatter(x=h.generation, y=h.best, name="Best", line=dict(color="#2ec4b6", width=4))
        fig.update_layout(title="Evolution of the population (convergence)", xaxis_title="Generation",
                          yaxis_title="Total cost", template="plotly_white", height=380, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # network diagram
        ys = lambda n: np.linspace(1, 0, n) if n > 1 else [0.5]
        pos = {("S", k_): (0, y) for k_, y in enumerate(ys(K))}
        pos |= {("W", i): (1, y) for i, y in enumerate(ys(I))}
        pos |= {("C", j): (2, y) for j, y in enumerate(ys(J))}
        net = go.Figure(); mx = max(r["x"].max(), r["z"].max())
        for M, a, b in [(r["x"], "S", "W"), (r["z"], "W", "C")]:
            for (p, q), v in np.ndenumerate(M):
                if v > 1e-6:
                    (x0, y0), (x1, y1) = pos[(a, p)], pos[(b, q)]
                    net.add_scatter(x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="text", showlegend=False,
                                    text=f"{v:,.1f} units", line=dict(width=1 + 5 * v / mx, color="rgba(31,111,139,.45)"))
        for t, n, names, col, sym in [("S", K, d.sup_names, "#f4a261", "square"), ("W", I, d.wh_names, None, "diamond"),
                                      ("C", J, d.cus_names, "#2a9d8f", "circle")]:
            colors = col or ["#e63946" if r["y"][i] else "#c9d3df" for i in range(n)]
            net.add_scatter(x=[pos[(t, i)][0] for i in range(n)], y=[pos[(t, i)][1] for i in range(n)],
                            mode="markers+text", text=names, textposition="middle right" if t != "C" else "middle right",
                            marker=dict(size=16, color=colors, symbol=sym), showlegend=False, textfont=dict(size=10))
        net.update_layout(title="Optimised network (red = open warehouse, grey = closed)", template="plotly_white",
                          height=620, xaxis=dict(visible=False, range=[-.2, 2.4]), yaxis=dict(visible=False))
        st.plotly_chart(net, use_container_width=True)

        st.subheader("Detailed flows")
        t1, t2, t3 = st.tabs(["Warehouses", "Supplier → Warehouse", "Warehouse → Customer"])
        wh_df = pd.DataFrame({"Warehouse": d.wh_names, "Status": np.where(r["y"] == 1, "OPEN", "closed"),
                              "Fixed cost": d.F * r["y"], "Capacity": d.Cap, "Load": r["z"].sum(1).round(2),
                              "Utilisation %": (100 * r["z"].sum(1) / d.Cap).round(1)})
        xdf = pd.DataFrame(r["x"].round(2), index=d.sup_names, columns=d.wh_names)
        zdf = pd.DataFrame(r["z"].round(2), index=d.wh_names, columns=d.cus_names)
        t1.dataframe(wh_df, hide_index=True, use_container_width=True)
        t2.dataframe(xdf, use_container_width=True); t3.dataframe(zdf, use_container_width=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            pd.DataFrame({"Metric": ["Total", "Fixed", "Upstream", "Downstream"],
                          "Cost": [r["total"], r["fixed"], r["upstream"], r["downstream"]]}).to_excel(w, sheet_name="Summary", index=False)
            wh_df.to_excel(w, sheet_name="Warehouses", index=False); xdf.to_excel(w, sheet_name="Flows_S_W"); zdf.to_excel(w, sheet_name="Flows_W_C")
            h.to_excel(w, sheet_name="GA_History", index=False)
        st.download_button("⬇️ Download solution (Excel)", buf.getvalue(), "solution.xlsx", type="primary")
