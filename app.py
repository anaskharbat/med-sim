# app.py — Outil « produits similaires » (MA) en local
# Streamlit UI + moteur simple de similarité par règles
# Dépendances: streamlit, pandas, rapidfuzz

import re
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st
from rapidfuzz import process, fuzz

# ---------------------------
# Config & chargement données
# ---------------------------
st.set_page_config(page_title="Simili Médicaments - Anas", page_icon="🌙", layout="wide",initial_sidebar_state="collapsed")

# ---------- THEME & BRANDING ----------
import streamlit as st

def inject_css(bg_primary="#0f172a", bg_secondary="#111827", sidebar_bg="#0b1320"):
    st.markdown(f"""
        <style>
            /* Fond principal (dégradé) */
            .stApp {{
                background: linear-gradient(180deg, {bg_primary} 0%, {bg_secondary} 100%) !important;
            }}
            /* Couleur de la sidebar */
            [data-testid="stSidebar"] > div:first-child {{
                background: {sidebar_bg} !important;
            }}
            /* Optionnel : coins arrondis légers */
            .stMarkdown, .stTextInput, .stSelectbox, .stMultiSelect, .stDataFrame {{
                border-radius: 12px;
            }}
        </style>
    """, unsafe_allow_html=True)

# Appelle la fonction une fois au chargement
inject_css(
    bg_primary="#0f172a",   # ← change ici la couleur principale si tu veux
    bg_secondary="#111827", # ← et la couleur du bas du dégradé
    sidebar_bg="#0b1320"    # ← couleur de la sidebar
)


DEFAULT_CSV = "data_full.csv"  # ton fichier produit par le parseur

@st.cache_data(show_spinner=False)
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    # Colonnes attendues par le moteur
    expected = {
        "specialite", "molecules", "grammages", "forme", "statut",
        "classe_therapeutique", "atc_code", "presentation",
        "composition_pretty", "dosage_pretty", "presentation_pretty",
        "detail_url", "labo"
    }
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.warning(f"Colonnes manquantes (ok si non bloquant) : {', '.join(missing)}")
        for m in missing:
            df[m] = ""
    # Prépare colonnes normalisées
    df["molecules_norm"] = df["molecules"].apply(lambda x: norm_pipes_lower(x))
    df["forme_norm"] = df["forme"].apply(norm_forme)
    df["grammages_norm"] = df["grammages"].apply(lambda x: norm_pipes_lower(x))
    df["brand_key"] = df["specialite"].apply(lambda s: strip_accents(s).lower())
    return df

# ---------------------------
# Normalisations / helpers
# ---------------------------
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
    """Transforme 'a | b | c' en set normalisé en minuscules sans accents."""
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
    #if row.get("detail_url",""): blocs.append(f"[Fiche détail]({row['detail_url']})")
    return "  \n".join(blocs)

# ---------------------------
# Moteur de similarité (règles)
# ---------------------------
def find_reference(df: pd.DataFrame, query: str) -> pd.Series | None:
    """Cherche la meilleure fiche de référence par fuzzy match sur spécialité + molécules."""
    if not query:
        return None
    # candidates on brand then on molecules (DCI)
    choices = df["specialite"].tolist()
    best = process.extractOne(query, choices, scorer=fuzz.WRatio)
    idx = None
    if best and best[1] >= 75:
        idx = df.index[choices.index(best[0])]
    else:
        # essaye par DCI (concat molécules)
        choices2 = df["molecules"].tolist()
        best2 = process.extractOne(query, choices2, scorer=fuzz.WRatio)
        if best2 and best2[1] >= 75:
            idx = df.index[choices2.index(best2[0])]
    if idx is None:
        # dernier recours : recherche partielle
        q = strip_accents(query).lower()
        hit = df.index[df["brand_key"].str.contains(q, na=False)].tolist()
        if hit:
            idx = hit[0]
    if idx is None:
        return None
    return df.loc[idx]

def group_similars(df: pd.DataFrame, ref: pd.Series) -> dict:
    """Retourne tiers A/B/C/D avec explications."""
    ref_mols = split_set_norm(ref.get("molecules_norm",""))
    ref_form = ref.get("forme_norm","")
    ref_dos  = split_set_norm(ref.get("grammages_norm",""))
    ref_atc  = (ref.get("atc_code","") or "").strip()

    tiers = {"A": [], "B": [], "C": [], "D": []}

    for _, r in df.iterrows():
        if r["specialite"] == ref["specialite"] and r["detail_url"] == ref["detail_url"]:
            continue

        mols = split_set_norm(r.get("molecules_norm",""))
        if not ref_mols or not mols:
            # pas d'info DCI : on ne peut classer qu'en D (ATC) à la fin
            pass

        same_inn = (mols == ref_mols and len(mols) > 0)
        same_form = (r.get("forme_norm","") == ref_form and ref_form != "")
        dos = split_set_norm(r.get("grammages_norm",""))

        # A — même DCI + même dosage (exact texte normalisé) + même forme
        if same_inn and same_form and dos and (dos == ref_dos):
            tiers["A"].append(r)
            continue
        # B — même DCI + même forme (dosage différent ou absent)
        if same_inn and same_form:
            tiers["B"].append(r)
            continue
        # C — même DCI (quelle que soit la forme)
        if same_inn:
            tiers["C"].append(r)
            continue
        # D — même ATC code (proche thérapeutique)
        if ref_atc and r.get("atc_code","").strip() == ref_atc:
            tiers["D"].append(r)
            continue

    # tri simple : statut commercialisé d’abord puis tri alpha
    def sort_key(sr):
      return (0 if (sr.get("statut","").lower().startswith("com")) else 1, sr.get("specialite",""))

    for k in tiers:
        tiers[k] = sorted(tiers[k], key=sort_key)

    return tiers

# ---------------------------
# UI
# ---------------------------
st.title("💊🌙 Simili Médicaments — test AK")

with st.sidebar:
    st.subheader("⚙️ Données")
    csv_path = st.text_input("Chemin du CSV", value=DEFAULT_CSV)
    if not Path(csv_path).exists():
        st.info("Indique le chemin vers `data_full.csv` généré par ton parseur.")
    df = load_data(csv_path) if Path(csv_path).exists() else pd.DataFrame()

    st.divider()
    st.subheader("Filtres")
    formes = sorted([f for f in df["forme_norm"].unique().tolist() if f])
    forme_filter = st.multiselect("Forme", formes, default=[])

    statuts = sorted([s for s in df["statut"].unique().tolist() if s])
    statut_filter = st.multiselect("Statut", statuts, default=[])

st.write("Tape un **nom commercial** (ex. *Doliprane*) ou une **DCI** (ex. *Paracétamol*).")
query = st.text_input("🔎 Rechercher un médicament", value="", placeholder="Nom commercial ou DCI...", label_visibility="visible")

if df.empty:
    st.stop()

# Appliquer filtres au corpus
mask = pd.Series(True, index=df.index)
if forme_filter:
    mask = mask & df["forme_norm"].isin(forme_filter)
if statut_filter:
    mask = mask & df["statut"].isin(statut_filter)
df_view = df[mask].copy()

# Trouver la référence
if query.strip():
    ref = find_reference(df_view, query.strip())
    if ref is None:
        st.warning("Aucun résultat proche. Essaie une autre orthographe ou enlève des filtres.")
        st.stop()

    st.success(f"**Référence :** {ref['specialite']} — {ref.get('forme','')}")
    with st.expander("Détails de la référence"):
        st.markdown(pretty_card(ref), unsafe_allow_html=True)

    tiers = group_similars(df_view, ref)

    # Affichage par colonnes
    colA, colB, colC, colD = st.columns(4)

    def show_bucket(col, title, rows):
        with col:
            st.markdown(f"### {title}  <small>{len(rows)} résultat(s)</small>", unsafe_allow_html=True)
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

    # # Export rapide
    # all_rows = []
    # for k in ["A","B","C","D"]:
    #     for r in tiers[k]:
    #         sr = r.copy()
    #         sr["similarity_tier"] = k
    #         all_rows.append(sr)
    # if all_rows:
    #     out_df = pd.DataFrame(all_rows)
    #     st.download_button("⬇️ Exporter résultats (CSV)", data=out_df.to_csv(index=False).encode("utf-8"), file_name="similaires_resultats.csv", mime="text/csv")
else:
    # suggestions (top brands)
    suggestions = (
        df_view.groupby("specialite", as_index=False)
               .size()
               .sort_values("size", ascending=False)
               .head(12)["specialite"]
               .tolist()
    )
    if suggestions:
        st.info("Exemples : " + " • ".join(suggestions))
