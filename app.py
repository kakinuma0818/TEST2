# app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import itertools

# -----------------------
# Config / Styling
# -----------------------
PRIMARY_COLOR = "#FF7F50"  # エルメスオレンジ
st.set_page_config(page_title="Keiba", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""
<style>
/* Font */
html, body, [class*="css"] {{ font-family: Helvetica, Arial, sans-serif; }}
/* Accent color */
.orange {{ color: {PRIMARY_COLOR}; font-weight: 600; }}
/* Button */
.stButton>button {{ background-color: {PRIMARY_COLOR}; color: white; border: none; }}
/* Tabs sticky (approx) */
section[data-testid="stHorizontalBlock"] {{ position: sticky; top: 0; z-index: 999; background: white; }}
/* DataFrame container */
div[data-testid="stDataFrameContainer"] {{ max-width: 100%; }}
</style>
""", unsafe_allow_html=True)

# -----------------------
# Sample data loader (replace with real scraper)
# -----------------------
def load_race_data_dummy():
    data = {
        "枠":[1,2,3,4,5,6],
        "馬番":[1,2,3,4,5,6],
        "馬名":["アドマイヤテラ","カランダガン","サンプルA","サンプルB","サンプルC","サンプルD"],
        "性齢":["牡4","セ4","牝3","牡5","牡6","牝4"],
        "斤量":[57,57,54,56,57,55],
        "前走体重":[500,502,470,480,488,472],
        "距離":[1800,2000,1600,1800,2000,1400],
        "脚質":["差し","先行","追込","逃げ","先行","差し"],
        "騎手":["川田","M.バルザローナ","武豊","福永","横山","池添"],
        "調教師":["(栗東)藤沢","(美浦)高木","(栗東)池江","(美浦)友道","(栗東)田中","(美浦)佐藤"],
        "オッズ":[3.2,5.1,12.5,7.8,20.0,15.0],
        "人気":[1,2,4,3,6,5],
        # ベーススコア（将来 calculate_all_scores で上書き）
        "ベーススコア":[85,78,70,72,65,68],
        "血統":["サンデー系","キングマンボ系","ミスプロ系","サンデー系","ノーザン系","ミスプロ系"],
        "馬主":["A","B","C","D","E","F"],
        "生産者":["X牧場","Y牧場","Z牧場","W牧場","V牧場","U牧場"],
        "成績":["1-2-1-2","0-1-1-3","2-0-1-2","1-1-0-3","0-0-1-4","1-1-2-1"],
        "馬場":["良","稍重","重","良","良","稍重"],
    }
    df = pd.DataFrame(data)
    return df

# Placeholder for production scoring logic
def calculate_all_scores(df):
    df = df.copy()
    # Ensure numeric base score column exists
    if "ベーススコア" not in df.columns:
        df["ベーススコア"] = 0
    df["ベーススコア"] = pd.to_numeric(df["ベーススコア"], errors="coerce").fillna(0)
    # initial 合計 is ベーススコア (manual applied later)
    return df

# simple auto allocation (placeholder)
def auto_allocate(amount, combos):
    n = max(1, len(combos))
    base = amount // n
    return {combo: base for combo in combos}

# -----------------------
# Session state init
# -----------------------
if "marks" not in st.session_state:
    st.session_state.marks = {}            # 馬名 -> 印
if "manual_scores" not in st.session_state:
    st.session_state.manual_scores = {}    # 馬名 -> manual
if "race_meta" not in st.session_state:
    st.session_state.race_meta = {}        # race selection

# -----------------------
# Sidebar: top selection
# -----------------------
with st.sidebar:
    st.header("レース選択")
    race_date = st.date_input("日付", date.today(), key="race_date")
    race_course = st.selectbox("競馬場", ["札幌","函館","福島","新潟","東京","中山","中京","京都","阪神","小倉"], key="race_course")
    race_number = st.selectbox("レース番号", list(range(1,13)), key="race_number")
    race_id_input = st.text_input("race_id (任意)", value="", help="netkeiba race_id を直接入力する場合")
    if st.button("更新 🔄"):
        st.session_state.race_meta = {
            "date": race_date.strftime("%Y%m%d"),
            "course": race_course,
            "number": race_number,
            "race_id": race_id_input
        }
        st.experimental_rerun()

# -----------------------
# Top overview (no big title)
# -----------------------
col1, col2, col3 = st.columns([2,6,2])
with col1:
    st.markdown(f"**{race_course} {race_number}R**")
with col2:
    race_name = st.text_input("レース名", value=st.session_state.race_meta.get("race_name",""))
    race_grade = st.selectbox("グレード", ["","G1","G2","G3","OP","条件"], key="race_grade")
    race_time = st.text_input("発走時刻", value=st.session_state.race_meta.get("race_time",""))
with col3:
    show_top6_bold = st.checkbox("MA: 上位6頭を太字表示", value=True)
    show_top3_highlight = st.checkbox("SC: 上位3を強調表示", value=True)

# -----------------------
# Load data (replace with real loader)
# -----------------------
df = load_race_data_dummy()
df = calculate_all_scores(df)

# init session keys
for name in df["馬名"]:
    st.session_state.marks.setdefault(name, "")
    st.session_state.manual_scores.setdefault(name, 0)

# compute 合計 column for display: 合計 = ベーススコア + manual
df["手動"] = df["馬名"].map(lambda n: st.session_state.manual_scores.get(n, 0))
df["合計"] = df["ベーススコア"] + df["手動"]

# -----------------------
# Tabs
# -----------------------
tabs = st.tabs(["出馬表","スコア","馬券","基本情報","成績"])
tab_ma, tab_sc, tab_be, tab_pr, tab_gr = tabs

# -----------------------
# 出馬表 Tab — exact order requested
# Columns order:
# 馬番, 馬名, 印, スコア(合計 shown), スコア順, オッズ, 人気, 性齢, 斤量, 前走体重, 調教師, 馬主
# -----------------------
with tab_ma:
    st.subheader("出馬表")

    sort_option = st.selectbox("並び替え", ["馬番順","スコア順","オッズ順","人気順"])
    if sort_option == "馬番順":
        df_display = df.sort_values("馬番", ascending=True).reset_index(drop=True)
    elif sort_option == "スコア順":
        df_display = df.sort_values("合計", ascending=False).reset_index(drop=True)
    elif sort_option == "オッズ順":
        df_display = df.sort_values("オッズ", ascending=True).reset_index(drop=True)
    else:
        df_display = df.sort_values("人気", ascending=True).reset_index(drop=True)

    # update marks (印) via selectboxes (persist keys)
    st.write("印を選択（各馬ごと）:")
    for i, r in df_display.iterrows():
        name = r["馬名"]
        st.session_state.marks[name] = st.selectbox(
            f"{r['馬番']}. {name} の印",
            options=["", "◎","○","▲","△","⭐︎","×"],
            index=(["", "◎","○","▲","△","⭐︎","×"].index(st.session_state.marks.get(name,"")) if st.session_state.marks.get(name,"") in ["","◎","○","▲","△","⭐︎","×"] else 0),
            key=f"mark_ma_{name}"
        )

    # prepare table to show
    df_display_show = df_display.copy()
    df_display_show["印"] = df_display_show["馬名"].map(lambda n: st.session_state.marks.get(n,""))
    df_display_show["スコア"] = df_display_show["合計"]  # display 合計 as スコア in MA
    # compute スコア順 (rank)
    df_display_show["スコア順"] = df_display_show["合計"].rank(method="min", ascending=False).astype(int)

    # reorder columns as requested
    cols_order = ["馬番","馬名","印","スコア","スコア順","オッズ","人気","性齢","斤量","前走体重","調教師","馬主"]
    for c in cols_order:
        if c not in df_display_show.columns:
            df_display_show[c] = ""
    df_show = df_display_show[cols_order].copy()

    # Styling: bold top6 by 合計
    def highlight_top6(row):
        if not show_top6_bold:
            return [''] * len(row)
        # Determine threshold of top6
        top6_vals = sorted(df["合計"], reverse=True)[:6]
        styles = []
        for val in row:
            # if this row's 合計 (we detect by column index) in top6 -> bold
            styles.append('font-weight:700;' if (isinstance(val,(int,float,np.integer,np.floating)) and val in top6_vals) else '')
        return styles

    # Use styler to bold entire row if its スコア in top6
    sty = df_show.style
    # Bold rows where スコア in top6
    top6 = sorted(df["合計"], reverse=True)[:6]
    def row_bold(s):
        return ['font-weight:700;' if (s['スコア'] in top6) else '' for _ in s]
    sty = sty.apply(row_bold, axis=1)

    st.dataframe(sty, use_container_width=True)

# -----------------------
# スコア Tab (SC)
# Left fixed: 馬名, 合計
# Show manual selectors and compute 合計 -> reflect in MA
# -----------------------
with tab_sc:
    st.subheader("スコア詳細")

    # Manual inputs
    st.write("手動スコア（-3〜+3）を入力：")
    for i, r in df.iterrows():
        name = r["馬名"]
        ms = st.selectbox(f"{name} の手動スコア", options=[-3,-2,-1,0,1,2,3],
                          index=[-3,-2,-1,0,1,2,3].index(st.session_state.manual_scores.get(name,0)),
                          key=f"manual_sc_{name}")
        st.session_state.manual_scores[name] = ms

    # Recompute 合計
    df["手動"] = df["馬名"].map(lambda n: st.session_state.manual_scores.get(n, 0))
    df["合計"] = df["ベーススコア"] + df["手動"]

    # Build display columns
    display_cols = ["馬名","合計","ベーススコア","性齢","血統","騎手","馬主","生産者","調教師","成績","競馬場","距離","脚質","枠","馬場","手動"]
    for c in display_cols:
        if c not in df.columns:
            df[c] = ""

    df_sc_show = df[display_cols].sort_values("合計", ascending=False).reset_index(drop=True)

    # highlight top3: color + bold
    top3_vals = sorted(df["合計"], reverse=True)[:3]
    def highlight_top3_cell(val):
        if val in top3_vals:
            return f'color: {PRIMARY_COLOR}; font-weight: 700;'
        return ''

    sty_sc = df_sc_show.style.applymap(lambda v: highlight_top3_cell(v) if isinstance(v,(int,float,np.integer,np.floating)) and v in top3_vals else '', subset=["合計"])
    # Note: Streamlit displays the styler
    st.dataframe(sty_sc, use_container_width=True)

# -----------------------
# 馬券 Tab (BE)
# -----------------------
with tab_be:
    st.subheader("馬券")
    st.write("Netkeiba風の簡易購入UI（実購入API未接続）")
    bet_type = st.selectbox("馬券種", ["単勝","複勝","ワイド","馬連","馬単","3連複","3連単"])
    horse_names = df["馬名"].tolist()
    selected = st.multiselect("選択馬（MA から選択）", horse_names)
    total_budget = st.number_input("総投資額 (円)", min_value=100, step=100, value=1000)
    auto_alloc = st.checkbox("自動分配（均等）", value=True)

    # Build combos depending on bet_type
    combos = []
    if bet_type in ["3連複","3連単"]:
        pool = selected if len(selected) >= 3 else df.sort_values("合計", ascending=False)["馬名"].tolist()[:6]
        combos = list(itertools.permutations(pool, 3)) if bet_type=="3連単" else list(itertools.combinations(pool, 3))
    elif bet_type in ["馬連","馬単","ワイド"]:
        pool = selected if len(selected) >= 2 else df.sort_values("合計", ascending=False)["馬名"].tolist()[:6]
        combos = list(itertools.permutations(pool, 2))
    else:
        pool = selected if selected else df.sort_values("合計", ascending=False)["馬名"].tolist()[:6]
        combos = [(h,) for h in pool]

    allocation = auto_allocate(total_budget, combos) if auto_alloc else {c:0 for c in combos}

    st.write(f"候補数: {len(combos)}")
    for i, combo in enumerate(list(combos)[:50]):
        combo_str = " - ".join(combo)
        alloc = allocation.get(combo,0)
        c0, c1, c2 = st.columns([4,2,2])
        c0.write(combo_str)
        c1.write(f"想定投資: {alloc} 円")
        allocation[combo] = c2.number_input(f"投資額 ({i})", min_value=0, step=50, value=int(alloc), key=f"alloc_be_{i}")

    total_spent = sum(allocation.values())
    st.write(f"合計投資額: {total_spent} 円 (設定総額: {total_budget} 円)")
    if st.button("仮購入（シミュレーション）"):
        st.success("購入シミュレーション完了（実購入未接続）")

# -----------------------
# 基本情報 (PR)
# -----------------------
with tab_pr:
    st.subheader("基本情報")
    df_pr = df[["馬名","性齢","血統","騎手","馬主","生産者","調教師","前走体重"]].copy()
    df_pr.rename(columns={"前走体重":"前走体重"}, inplace=True)
    st.dataframe(df_pr, use_container_width=True)

# -----------------------
# 成績 (GR)
# -----------------------
with tab_gr:
    st.subheader("成績（直近5戦）")
    df_gr = pd.DataFrame({
        "馬名": df["馬名"],
        "直近5戦（着順）": df["成績"]
    })
    st.dataframe(df_gr, use_container_width=True)

# Footer
st.markdown("---")
st.caption("本番用UI（最終形態）。データ取得・精密スコアリング・オッズのリアル接続はこの基盤へ組み込みます。")
