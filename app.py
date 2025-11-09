# app.py — Similaires Médicaments – Maroc
# Thème Medicalis Blue + Vert Santé (clair) + correctifs expanders + suggestions
# Streamlit >= 1.33

import unicodedata
from pathlib import Path
import pandas as pd
import streamlit as st

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Similaires Médicaments – Maroc",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------- THEME (FORCE CLAIR + STYLES) ----------------
def inject_theme():
    st.markdown(r"""
    <style>
    /* Force le thème Streamlit en clair (corrige la barre noire des expanders) */
    :root, html, body, [data-testid="stAppViewContainer"]{
      --background-color: #f6fbff;
      --secondary-background-color: #f9fcff;
      --text-color: #0f172a;
      --font: ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial;
    }

    :root{
      --panel:#ffffff; --accent:#ebf8ff;
      --primary:#2563eb; --primary-light:#60a5fa;
      --success:#10b981; --success-light:#d1fae5;
      --muted:#475569; --border:#dbeafe; --ring:#bfdbfe;
      --shadow:0 10px 25px rgba(2,6,23,.06);
    }

    .stApp{
      background:
        radial-gradient(1200px 600px at 0% 0%, var(--accent), transparent 60%),
        radial-gradient(1200px 600px at 110% 10%, var(--accent), transparent 55%),
        var(--background-color) !important;
      color: var(--text-color) !important;
      font-family: var(--font) !important;
    }
    a{ color:#0ea5e9 !important; text-decoration:none; }
    a:hover{ text-decoration:underline; }

    /* Header clair (enlève la barre sombre en haut) */
    header[data-testid="stHeader"]{
      background-color:#f6fbff !important;
      color:var(--text-color) !important;
      border-bottom:1px solid var(--border) !important;
      box-shadow:0 2px 8px rgba(59,130,246,.08) !important;
    }
    header[data-testid="stHeader"] [data-testid="baseButton-header"]{
      background:transparent !important; color:var(--text-color) !important;
    }
    header[data-testid="stHeader"] [data-testid="baseButton-header"]:hover{
      background:#eef6ff !important;
    }

    /* Hero */
    .hero{
      background:linear-gradient(135deg,#eff6ff,#ecfdf5 60%,#eff6ff);
      border:1px solid var(--border);
      border-radius:22px; padding:24px 26px;
      box-shadow:var(--shadow); transition:all .3s ease;
    }
    .hero:hover{ box-shadow:0 15px 35px rgba(37,99,235,.15); transform:translateY(-2px); }
    .hero-badge{
      width:48px;height:48px;border-radius:16px;
      background:linear-gradient(135deg,#3b82f6,#10b981);
      display:flex;align-items:center;justify-content:center;
      color:white;font-weight:900;font-size:22px;
      box-shadow:0 10px 25px rgba(37,99,235,.25);
    }
    .hero h1{ margin:0; }
    .hero .subtitle{ color:var(--muted); }

    /* Inputs / boutons */
    .stTextInput input, .stSelectbox>div, .stMultiSelect>div{
      background:var(--panel)!important; border:1px solid var(--border)!important;
      border-radius:14px!important; color:var(--text-color)!important;
      box-shadow:0 1px 2px rgba(2,6,23,.05) inset;
    }
    .stTextInput input:focus{ outline:3px solid var(--ring)!important; border-color:#93c5fd!important; }
    .stButton>button{
      border-radius:14px!important;
      border:1px solid var(--border)!important;
      background:linear-gradient(135deg,#3b82f6,#10b981)!important;
      color:#fff!important;font-weight:700!important;letter-spacing:.2px;
      padding:6px 20px!important; box-shadow:0 10px 25px rgba(59,130,246,.25);
      transition:.25s ease;
    }
    .stButton>button:hover{
      transform:translateY(-1px); filter:brightness(1.08);
      box-shadow:0 12px 30px rgba(37,99,235,.35);
    }

    /* Cartes */
    .card{ background:var(--panel); border:1px solid var(--border);
      border-radius:18px; padding:16px; box-shadow:var(--shadow);
      transition:all .3s ease; }
    .card:hover{ box-shadow:0 10px 35px rgba(16,185,129,.15); }

    /* >>> EXPANDERS : on neutralise totalement le fond sombre du summary */
    details[data-testid="stExpander"]{
      background:var(--panel)!important; border:1px solid var(--border)!important; border-radius:16px!important;
      color:var(--text-color)!important; transition:all .3s ease;
    }
    /* Summary et descendants */
    details[data-testid="stExpander"] summary,
    details[data-testid="stExpander"] summary *{
      background-color:#f9fcff !important;
      color:var(--text-color) !important;
      border-radius:12px !important;
      border:1px solid var(--border) !important;
      padding:6px 10px !important;
      filter:none !important;
    }
    /* Hover */
    details[data-testid="stExpander"] summary:hover,
    details[data-testid="stExpander"] summary:hover *{
      background-color:#eef6ff !important;
      color:var(--text-color) !important;
      border-color:#bfdbfe !important;
      box-shadow:0 3px 8px rgba(37,99,235,.08);
    }
    /* Open */
    details[data-testid="stExpander"][open] summary,
    details[data-testid="stExpander"][open] summary *{
      background-color:#f0f7ff !important;
      border-color:#bfdbfe !important;
      color:var(--text-color) !important;
      box-shadow:0 3px 8px rgba(37,99,235,.08);
    }
    /* Focus */
    details[data-testid="stExpander"] summary:focus,
    details[data-testid="stExpander"] summary:active{
      outline:none !important;
      box-shadow:0 0 0 2px rgba(37,99,235,.25);
    }
    /* Marqueur */
    details[data-testid="stExpander"] summary::marker{ color:#3b82f6 !important; }
    details[data-testid="stExpander"][open] summary::marker{ color:#10b981 !important; }

    /* Pastilles statut */
    .status{ padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid var(--border); display:inline-block; }
    .status.ok{ background:var(--success-light); color:var(--success)!important; }
    .status.off{ background:#fff1f1; color:#ef4444!important; }
    /* ==== EXPANDER : pas de hover, pas de noir, style constant ==== */
    details[data-testid="stExpander"] summary,
    details[data-testid="stExpander"] summary * {
      background: #f9fcff !important;            /* fond clair constant */
      color: var(--text-color, #0f172a) !important;
      border: 1px solid var(--border, #dbeafe) !important;
      border-radius: 12px !important;
      padding: 8px 12px !important;
      box-shadow: none !important;
      filter: none !important;
      transition: none !important;               /* supprime les effets */
    }
    
    /* Bloque tous les états visuels */
    details[data-testid="stExpander"] summary:hover,
    details[data-testid="stExpander"] summary:active,
    details[data-testid="stExpander"] summary:focus,
    details[data-testid="stExpander"][open] summary,
    details[data-testid="stExpander"][open] summary * {
      background: #f9fcff !important;
      color: var(--text-color, #0f172a) !important;
      border-color: var(--border, #dbeafe) !important;
      box-shadow: none !important;
      filter: none !important;
      outline: none !important;
    }
    
    /* (optionnel) icône/chevron couleur fixe */
    details[data-testid="stExpander"] summary [data-testid="stIconMaterial"]{
      color: #3b82f6 !important;
    }
           

    </style>
    """, unsafe_allow_html=True)

inject_theme()

# ---------------- HERO ----------------
st.markdown("""
<div class="hero">
  <div style="display:flex;align-items:center;gap:14px;">
    <div class="hero-badge">💊</div>
    <div>
      <h1>Similaires Médicaments – Maroc</h1>
      <div class="subtitle">Compare et découvre les médicaments similaires selon leur composition et usage.</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------
def strip_accents(s: str) -> str:
    if not s: return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_pipes_lower(x: str) -> str:
    if not x: return ""
    x = x.replace(" / ", " | ").replace("/", " / ")
    if "|" not in x and "," in x:
        x = " | ".join([p.strip() for p in x.split(",")])
    parts = [strip_accents(p).lower().strip() for p in x.split("|") if p.strip()]
    return " | ".join(parts)

def norm_forme(x: str) -> str:
    s = strip_accents(str(x)).lower().strip()
    s = s.replace("comp.", "comprime").replace("cp", "comprime")
    if "comprime" in s: return "COMPRIME"
    if "gelule" in s: return "GELULE"
    if "sirop" in s: return "SIROP"
    if "solution" in s: return "SOLUTION"
    if "poudre" in s: return "POUDRE"
    if "capsule" in s: return "CAPSULE"
    if "suspension" in s: return "SUSPENSION"
    if "collyre" in s: return "COLLYRE"
    return s.upper()[:40] if s else ""

def split_set_norm(x: str) -> set:
    if not x: return set()
    return {strip_accents(t).lower().strip() for t in x.split("|") if t.strip()}

def pretty_card(row: pd.Series) -> str:
    p = row.get("presentation_pretty","") or row.get("presentation","")
    d = row.get("dosage_pretty","") or row.get("grammages","")
    comp = row.get("composition_pretty","") or row.get("molecules","")
    bloc = []
    if p: bloc.append(f"**Présentation** : {p}")
    if d: bloc.append(f"**Dosage** : {d}")
    if row.get("labo",""): bloc.append(f"**Distributeur / Fab.** : {row['labo']}")
    if comp: bloc.append(f"**Composition** : {comp}")
    if row.get("classe_therapeutique",""): bloc.append(f"**Classe thérapeutique** : {row['classe_therapeutique']}")
    if row.get("statut",""): bloc.append(f"**Statut** : {row['statut']}")
    if row.get("atc_code",""): bloc.append(f"**Code ATC** : {row['atc_code']}")
    return "  \n".join(bloc)

# ---------------- DATA ----------------
DEFAULT_CSV = "data_full_with_dr_luna.csv"

@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    expected = {
        "specialite","molecules","grammages","forme","statut",
        "classe_therapeutique","atc_code","presentation",
        "composition_pretty","dosage_pretty","presentation_pretty",
        "detail_url","labo"
    }
    for m in expected:
        if m not in df.columns: df[m] = ""
    df["molecules_norm"]  = df["molecules"].apply(norm_pipes_lower)
    df["forme_norm"]      = df["forme"].apply(norm_forme)
    df["grammages_norm"]  = df["grammages"].apply(norm_pipes_lower)
    df["brand_key"]       = df["specialite"].apply(lambda s: strip_accents(s).lower())
    return df

# ---------------- LOGIQUE DE SIMILARITÉ ----------------
def find_reference(df: pd.DataFrame, query: str) -> pd.Series | None:
    if not query: return None
    qn = strip_accents(query).lower().strip()
    brand_norm = df["specialite"].astype(str).apply(lambda s: strip_accents(s).lower())
    mask_sw = brand_norm.str.startswith(qn)
    if mask_sw.any():
        return df[mask_sw].iloc[0]
    # Fallback fuzzy (optionnel)
    try:
        from rapidfuzz import process, fuzz
        best = process.extractOne(query, df["specialite"].tolist(), scorer=fuzz.WRatio)
        if best and best[1] >= 75:
            return df.iloc[df["specialite"].tolist().index(best[0])]
        best2 = process.extractOne(query, df["molecules"].tolist(), scorer=fuzz.WRatio)
        if best2 and best2[1] >= 75:
            return df.iloc[df["molecules"].tolist().index(best2[0])]
    except Exception:
        pass
    if "brand_key" in df.columns:
        ct = df["brand_key"].str.contains(qn, na=False)
        if ct.any(): return df[ct].iloc[0]
    return None

def group_similars(df: pd.DataFrame, ref: pd.Series) -> dict:
    ref_mols = split_set_norm(ref.get("molecules_norm",""))
    ref_form = ref.get("forme_norm","")
    ref_dos  = split_set_norm(ref.get("grammages_norm",""))
    ref_atc  = (ref.get("atc_code","") or "").strip()
    tiers = {"A": [], "B": [], "C": [], "D": []}
    for _, r in df.iterrows():
        if r["specialite"] == ref["specialite"] and r.get("detail_url","") == ref.get("detail_url",""):
            continue
        mols = split_set_norm(r.get("molecules_norm",""))
        same_inn_exact  = (mols == ref_mols and len(mols) > 0)
        same_inn_subset = (len(ref_mols) > 0 and ref_mols.issubset(mols))
        same_form       = (r.get("forme_norm","") == ref_form and ref_form != "")
        dos             = split_set_norm(r.get("grammages_norm",""))
        if same_inn_exact and same_form and dos and (dos == ref_dos):
            tiers["A"].append(r); continue
        if (same_inn_exact or same_inn_subset) and same_form:
            tiers["B"].append(r); continue
        if (same_inn_exact or same_inn_subset):
            tiers["C"].append(r); continue
        if ref_atc and r.get("atc_code","").strip() == ref_atc:
            tiers["D"].append(r); continue
    def sort_key(sr):
        return (0 if (str(sr.get("statut","")).lower().startswith("com")) else 1, sr.get("specialite",""))
    for k in tiers:
        tiers[k] = sorted(tiers[k], key=sort_key)
    return tiers

# ---------------- STATE : input robuste + suggestions qui remplissent ----------------
if "query" not in st.session_state:
    st.session_state["query"] = ""
if "pending_query" in st.session_state:
    st.session_state["query"] = st.session_state.pop("pending_query")

# ---------------- INTERFACE ----------------
with st.sidebar:
    st.markdown("### ⚙️ Données")
    csv_path = st.text_input("Chemin du CSV", value=DEFAULT_CSV)
    df = load_data(csv_path) if Path(csv_path).exists() else pd.DataFrame()
    st.markdown("### 🔎 Filtres")
    formes = sorted([f for f in df.get("forme_norm", pd.Series()).unique().tolist() if f]) if not df.empty else []
    forme_filter = st.multiselect("Forme", formes, default=[])
    statuts = sorted([s for s in df.get("statut", pd.Series()).unique().tolist() if s]) if not df.empty else []
    statut_filter = st.multiselect("Statut", statuts, default=[])

query = st.text_input("Rechercher", placeholder="Nom commercial ou DCI…",
                      label_visibility="collapsed", key="query")

if df.empty: st.stop()
mask = pd.Series(True, index=df.index)
if forme_filter: mask &= df["forme_norm"].isin(forme_filter)
if statut_filter: mask &= df["statut"].isin(statut_filter)
df_view = df[mask].copy()

# ---------------- AUTOCOMPLÉTION ----------------
def suggest_matches(df_src, q, max_suggestions=8):
    qn = strip_accents(q).lower().strip()
    if not qn: return []
    brands = df_src["specialite"].astype(str).tolist()
    dci = df_src["molecules"].astype(str).tolist()
    combos = brands + dci
    seen, out = set(), []
    for val in combos:
        vn = strip_accents(val).lower()
        if vn.startswith(qn) and val not in seen:
            out.append(val); seen.add(val)
            if len(out)>=max_suggestions: break
    if len(out)<max_suggestions:
        for val in combos:
            vn = strip_accents(val).lower()
            if qn in vn and val not in seen:
                out.append(val); seen.add(val)
                if len(out)>=max_suggestions: break
    return out[:max_suggestions]

if query.strip():
    sugs = suggest_matches(df_view, query)
    if sugs:
        st.caption("Suggestions :")
        cols = st.columns(min(6, len(sugs)))
        for i,s in enumerate(sugs):
            with cols[i%len(cols)]:
                if st.button(s, key=f"sugg_{i}_{abs(hash(s))%100000}"):
                    st.session_state["pending_query"] = s
                    st.rerun()

# ---------------- RÉSULTATS ----------------
def status_pill(text: str) -> str:
    if not text: return ""
    cls = "ok" if str(text).lower().startswith("com") else "off"
    return f'<span class="status {cls}">{text}</span>'

if query.strip():
    ref = find_reference(df_view, query.strip())
    if ref is None:
        st.warning("Aucun résultat proche. Essaie une autre orthographe ou enlève des filtres.")
        st.stop()

    st.markdown(f'<div class="card"><h3 style="margin:0;">Référence : {ref["specialite"]} — {ref.get("forme","")}</h3></div>', unsafe_allow_html=True)
    with st.expander("Voir les détails de la référence", expanded=False):
        st.markdown(pretty_card(ref), unsafe_allow_html=True)

    tiers = group_similars(df_view, ref)
    colA, colB, colC, colD = st.columns(4)

    def show_bucket(col, title, rows):
        with col:
            st.markdown(f"<div class='tier-title'><h3>{title}</h3> <span class='badge'>{len(rows)} résultat(s)</span></div>", unsafe_allow_html=True)
            if not rows:
                st.caption("Rien pour le moment. Affine la recherche ou les filtres.")
                return
            for r in rows[:200]:
                label = f"{r['specialite']} — {r.get('forme','')}"
                with st.expander(label, expanded=False):
                    line = f"DCI : {r.get('molecules','')}"
                    atc  = f" | ATC : {r.get('atc_code','')}" if r.get('atc_code','') else ""
                    st.caption(line + atc)
                    st.markdown(pretty_card(r), unsafe_allow_html=True)
                    st.markdown(status_pill(r.get("statut","")), unsafe_allow_html=True)

    show_bucket(colA, "A — Substituables", tiers["A"])
    show_bucket(colB, "B — Équivalents (forme =)", tiers["B"])
    show_bucket(colC, "C — Même DCI (formes ≠)", tiers["C"])
    show_bucket(colD, "D — Proches thérapeutiques (ATC)", tiers["D"])
else:
    st.markdown('<div class="card"><em>Commence à taper un médicament pour lancer la recherche.</em></div>', unsafe_allow_html=True)
