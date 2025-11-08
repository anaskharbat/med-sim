
# app_cloud.py — Streamlit app robuste (MA) avec fallback sans rapidfuzz
import os
import re
import unicodedata
from pathlib import Path

import streamlit as st
import pandas as pd

# --- Fallback RapidFuzz ---
try:
    from rapidfuzz import process, fuzz
    HAVE_RAPIDFUZZ = True
except Exception:
    import difflib
    HAVE_RAPIDFUZZ = False

    class _FuzzWrap:
        WRatio = None

    class _ProcessWrap:
        @staticmethod
        def extractOne(query, choices, scorer=None):
            if not choices:
                return None
            match = difflib.get_close_matches(query, choices, n=1, cutoff=0)
            if match:
                return (match[0], 100, 0)
            return None

    process = _ProcessWrap()
    fuzz = _FuzzWrap()

st.set_page_config(
    page_title=" Simili Médicaments — LUNA",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def inject_css(bg_primary="#0f172a", bg_secondary="#111827", sidebar_bg="#0b1320"):
    st.markdown(f"""
        <style>
            .stApp {{
                background: linear-gradient(180deg, {bg_primary} 0%, {bg_secondary} 100%) !important;
            }}
            [data-testid="stSidebar"] > div:first-child {{
                background: {sidebar_bg} !important;
            }}
        </style>
    """, unsafe_allow_html=True)

inject_css()

def strip_accents(s: str) -> str:
    if not s:
        return s
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def norm_pipes_lower(x: str) -> str:
    if not x:
        return ""
    x = x.replace(" / ", " | ").replace("/", " / ")
    if "|" not in x and "," in x:
        x = " | ".join([p.strip() for p in x.split(",")])
    parts = [p.strip().lower() for p in x.split("|") if p.strip()]
    return " | ".join(parts)

def norm_pipes_pretty(x: str) -> str:
    if not x:
        return ""
    x = x.replace(" / ", " | ").replace("/", " / ")
    if "|" not in x and "," in x:
        x = " | ".join([p.strip() for p in x.split(",")])
    parts = [p.strip() for p in x.split("|") if p.strip()]
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
    if not x:
        return set()
    return {strip_accents(t).lower().strip() for t in x.split("|") if t.strip()}

def pretty_card(row: pd.Series) -> str:
    p = norm_pipes_pretty(row.get("presentation_pretty", "")) or row.get("presentation","")
    d = norm_pipes_pretty(row.get("dosage_pretty", "")) or row.get("grammages","")
    comp = row.get("composition_pretty","") or row.get("molecules","")
    blocs = []
    if p: blocs.append(f"**Présentation** : {p}")
    if d: blocs.append(f"**Dosage** : {d}")
    if row.get("labo",""): blocs.append(f"**Distributeur / Fab.** : {row['labo']}")
    if comp: blocs.append(f"**Composition** : {comp}")
    if row.get("classe_therapeutique",""): blocs.append(f"**Classe thérapeutique** : {row['classe_therapeutique']}")
    if row.get("statut",""): blocs.append(f"**Statut** : {row['statut']}")
    if row.get("atc_code",""): blocs.append(f"**Code ATC** : {row['atc_code']}")
    if row.get("detail_url",""): blocs.append(f"[Fiche détail]({row['detail_url']})")
    return "  \n".join(blocs)

@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    if not Path(csv_path).exists():
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    expected = {
        "specialite", "molecules", "grammages", "forme", "statut",
        "classe_therapeutique", "atc_code", "presentation",
        "composition_pretty", "dosage_pretty", "presentation_pretty",
        "detail_url", "labo"
    }
    for m in expected:
        if m not in df.columns:
            df[m] = ""
    df["molecules_norm"] = df["molecules"].apply(lambda x: norm_pipes_lower(x))
    df["forme_norm"] = df["forme"].apply(norm_forme)
    df["grammages_norm"] = df["grammages"].apply(lambda x: norm_pipes_lower(x))
    df["brand_key"] = df["specialite"].apply(lambda s: strip_accents(s).lower())
    return df

def find_reference(df: pd.DataFrame, query: str) -> pd.Series | None:
    if not query:
        return None
    choices = df["specialite"].tolist()
    best = process.extractOne(query, choices, scorer=getattr(fuzz, "WRatio", None))
    idx = None
    if best and (best[1] >= 75 or not HAVE_RAPIDFUZZ):
        idx = df.index[choices.index(best[0])]
    else:
        choices2 = df["molecules"].tolist()
        best2 = process.extractOne(query, choices2, scorer=getattr(fuzz, "WRatio", None))
        if best2 and (best2[1] >= 75 or not HAVE_RAPIDFUZZ):
            idx = df.index[choices2.index(best2[0])]
    if idx is None:
        q = strip_accents(query).lower()
        hit = df.index[df["brand_key"].str.contains(q, na=False)].tolist()
        if hit:
            idx = hit[0]
    return df.loc[idx] if idx is not None else None

def group_similars(df: pd.DataFrame, ref: pd.Series) -> dict:
    ref_mols = split_set_norm(ref.get("molecules_norm",""))
    ref_form = ref.get("forme_norm","")
    ref_dos  = split_set_norm(ref.get("grammages_norm",""))
    ref_atc  = (ref.get("atc_code","") or "").strip()

    tiers = {"A": [], "B": [], "C": [], "D": []}

    for _, r in df.iterrows():
        if r["specialite"] == ref["specialite"] and r["detail_url"] == ref["detail_url"]:
            continue
        mols = split_set_norm(r.get("molecules_norm",""))
        same_inn = (mols == ref_mols and len(mols) > 0)
        same_form = (r.get("forme_norm","") == ref_form and ref_form != "")
        dos = split_set_norm(r.get("grammages_norm",""))

        if same_inn and same_form and dos and (dos == ref_dos):
            tiers["A"].append(r); continue
        if same_inn and same_form:
            tiers["B"].append(r); continue
        if same_inn:
            tiers["C"].append(r); continue
        if ref_atc and r.get("atc_code","").strip() == ref_atc:
            tiers["D"].append(r); continue

    def sort_key(sr):
        return (0 if (sr.get("statut","").lower().startswith("com")) else 1, sr.get("specialite",""))
    for k in tiers:
        tiers[k] = sorted(tiers[k], key=sort_key)
    return tiers

st.title("💊🌙 Simili Médicaments — test Anas")
DEFAULT_CSV = "data_full.csv"
csv_exists = Path(DEFAULT_CSV).exists()

with st.sidebar:
    st.subheader("⚙️ Données")
    if csv_exists:
        st.caption("Chargement depuis `data_full.csv` (dépôt).")
    else:
        st.caption("Aucun `data_full.csv` trouvé — charge ton fichier ci-dessous.")
    up = st.file_uploader("Importer un data_full.csv", type=["csv"], accept_multiple_files=False)

if csv_exists:
    df = load_data(DEFAULT_CSV)
elif up is not None:
    df = pd.read_csv(up, dtype=str).fillna("")
    if "molecules_norm" not in df.columns:
        df["molecules_norm"] = df["molecules"].apply(lambda x: norm_pipes_lower(x))
    if "forme_norm" not in df.columns:
        df["forme_norm"] = df["forme"].apply(norm_forme)
    if "grammages_norm" not in df.columns:
        df["grammages_norm"] = df["grammages"].apply(lambda x: norm_pipes_lower(x))
    if "brand_key" not in df.columns:
        df["brand_key"] = df["specialite"].apply(lambda s: strip_accents(s).lower())
else:
    st.warning("Aucune donnée trouvée. Ajoute `data_full.csv` au dépôt ou charge un fichier via la sidebar.")
    st.stop()

with st.sidebar:
    st.divider()
    st.subheader("Filtres")
    formes = sorted([f for f in df["forme_norm"].unique().tolist() if f])
    forme_filter = st.multiselect("Forme", formes, default=[])
    statuts = sorted([s for s in df["statut"].unique().tolist() if s])
    statut_filter = st.multiselect("Statut", statuts, default=[])

st.write("Tape un **nom commercial** (ex. *ANDOL 1000 MG*) ou une **DCI** (ex. *Acide acétylsalicylique*).")
query = st.text_input("🔎 Rechercher un médicament", value="", placeholder="Nom commercial ou DCI...")

mask = pd.Series(True, index=df.index)
if forme_filter:
    mask = mask & df["forme_norm"].isin(forme_filter)
if statut_filter:
    mask = mask & df["statut"].isin(statut_filter)
df_view = df[mask].copy()

if not query.strip():
    st.stop()

ref = find_reference(df_view, query.strip())
if ref is None:
    st.warning("Aucun résultat proche. Essaie une autre orthographe ou enlève des filtres.")
    st.stop()

st.success(f"**Référence :** {ref['specialite']} — {ref.get('forme','')}")
with st.expander("Voir les détails de la référence", expanded=False):
    st.markdown(pretty_card(ref), unsafe_allow_html=True)

tiers = group_similars(df_view, ref)

colA, colB, colC, colD = st.columns(4)

def show_bucket(col, title, rows):
    with col:
        st.markdown(f"### {title}  \n<small>{len(rows)} résultat(s)</small>", unsafe_allow_html=True)
        for r in rows[:200]:
            label = f"{r['specialite']} — {r.get('forme','')}"
            with st.expander(label, expanded=False):
                st.caption(f"DCI: {r.get('molecules','')}")
                st.markdown(pretty_card(r), unsafe_allow_html=True)
            st.divider()

show_bucket(colA, "A — Substituables (même DCI/dosage/forme)", tiers["A"])
show_bucket(colB, "B — Équivalents (même DCI/forme)", tiers["B"])
show_bucket(colC, "C — Même DCI (formes proches)", tiers["C"])
show_bucket(colD, "D — Proches thérapeutiques (ATC)", tiers["D"])
