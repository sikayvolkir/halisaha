import streamlit as st
from supabase import create_client, Client
import random
from datetime import date

# ---------------------------------------------------------
# Sayfa Konfigürasyonu & Tema (Futbol Sahası Dahil CSS)
# ---------------------------------------------------------
st.set_page_config(page_title="Halısaha Takip", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0d1117;
        color: #f0f6fc;
    }
    .main-title {
        color: #2ea44f;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .stButton > button {
        background-color: #238636;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 8px 16px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #2ea44f;
        color: white;
    }
    .card {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    /* Yatay Futbol Sahası Stil Tasarımı */
    .football-pitch {
        background-color: #2e7d32;
        background-image: linear-gradient(to right, rgba(255,255,255,0.1) 50%, transparent 50%);
        background-size: 80px 100%;
        border: 4px solid #ffffff;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        position: relative;
        min-height: 280px;
    }
    .pitch-center-line {
        position: absolute;
        left: 50%;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: rgba(255, 255, 255, 0.7);
    }
    .team-box {
        background: rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        padding: 10px;
        color: white;
    }
    .player-chip {
        background-color: #1f6feb;
        color: white;
        padding: 4px 8px;
        margin: 4px;
        border-radius: 15px;
        display: inline-block;
        font-size: 0.90rem;
        font-weight: 500;
    }
    .player-chip-b {
        background-color: #da3633;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Supabase Bağlantısı
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Session State Yönetimi
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_group" not in st.session_state:
    st.session_state.selected_group = None

def get_profile_name(profile_data):
    if isinstance(profile_data, dict):
        return profile_data.get("full_name", "Bilinmeyen Oyuncu")
    elif isinstance(profile_data, list) and len(profile_data) > 0:
        return profile_data[0].get("full_name", "Bilinmeyen Oyuncu")
    return "Bilinmeyen Oyuncu"

# ---------------------------------------------------------
# Kimlik Doğrulama Ekranı
# ---------------------------------------------------------
def auth_screen():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        st.subheader("Giriş Yap")
        email = st.text_input("E-Posta", key="login_email")
        password = st.text_input("Şifre", type="password", key="login_password")
        if st.button("Giriş Yap", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("Giriş başarılı!")
                st.rerun()
            except Exception as e:
                st.error(f"Giriş başarısız: {e}")

    with tab2:
        st.subheader("Yeni Hesap Oluştur")
        full_name = st.text_input("Ad Soyad", key="reg_name")
        email = st.text_input("E-Posta", key="reg_email")
        password = st.text_input("Şifre (En az 6 karakter)", type="password", key="reg_password")
        if st.button("Kayıt Ol", use_container_width=True):
            if not full_name.strip():
                st.warning("Lütfen adınızı ve soyadınızı girin.")
                return
            try:
                res = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                    "options": {"data": {"full_name": full_name}}
                })
                st.success("Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
            except Exception as e:
                st.error(f"Kayıt işlemi başarısız: {e}")

# ---------------------------------------------------------
# Ana Dashboard
# ---------------------------------------------------------
def main_dashboard():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA GRUPLARIM</h1>", unsafe_allow_html=True)
    user_id = st.session_state.user.id
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Dahil Olduğunuz Gruplar")
        memberships = supabase.table("group_members").select("group_id, is_admin, groups(id, name)").eq("user_id", user_id).execute()
        
        if memberships.data:
            for item in memberships.data:
                group = item.get("groups")
                if not group:
                    continue
                is_admin = item["is_admin"]
                with st.container():
                    st.markdown(f"<div class='card'><h3>{group['name']} {'⭐ (Admin)' if is_admin else ''}</h3></div>", unsafe_allow_html=True)
                    if st.button(f"Gruba Git: {group['name']}", key=f"btn_{group['id']}"):
                        st.session_state.selected_group = {
                            "id": group["id"],
                            "name": group["name"],
                            "is_admin": is_admin
                        }
                        st.rerun()
        else:
            st.info("Henüz herhangi bir gruba dahil değilsiniz.")

    with col2:
        st.subheader("Yeni Grup Oluştur")
        new_group_name = st.text_input("Grup Adı")
        if st.button("Grubu Kur", use_container_width=True):
            if new_group_name.strip():
                try:
                    group_res = supabase.table("groups").insert({
                        "name": new_group_name.strip(),
                        "created_by": user_id
                    }).execute()
                    new_group_id = group_res.data[0]["id"]
                    supabase.table("group_members").insert({
                        "group_id": new_group_id,
                        "user_id": user_id,
                        "is_admin": True
                    }).execute()
                    st.success("Grup başarıyla oluşturuldu!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Grup oluşturulurken hata: {e}")
            else:
                st.warning("Lütfen bir grup adı girin.")

# ---------------------------------------------------------
# Futbol Sahasında Kadro Gösterme Bileşeni
# ---------------------------------------------------------
def render_pitch(team_a, team_b):
    st.markdown("<div class='football-pitch'><div class='pitch-center-line'></div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("<div class='team-box'><h4>🔵 A Takımı</h4>", unsafe_allow_html=True)
        for p in team_a:
            st.markdown(f"<span class='player-chip'>{p}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='team-box'><h4>🔴 B Takımı</h4>", unsafe_allow_html=True)
        for p in team_b:
            st.markdown(f"<span class='player-chip player-chip-b'>{p}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Grup Detay ve Gelecek Maçlar Ekranı
# ---------------------------------------------------------
def group_detail():
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)
    
    tab_upcoming, tab_create, tab_past, tab_leaderboard = st.tabs(
        ["📅 Gelecek Maçlar & Kadrolar", "➕ Maç Planla", "📜 Geçmiş Maçlar", "🏆 Puan Sıralaması"]
    )
    
    today_str = str(date.today())
    
    # Tüm Maçları Çek ve Python Tarafında Filtrele (Tarih Hatalarını Önler)
    all_matches = supabase.table("matches").select("*").eq("group_id", group["id"]).execute()
    matches_list = all_matches.data if all_matches.data else []

    # =========================================================
    # TAB 1: GELECEK MAÇLAR VE KADRO KURMA
    # =========================================================
    with tab_upcoming:
        st.subheader("📅 Gelecek Maçlar ve Kadro Planlaması")
        upcoming_matches_data = [m for m in matches_list if str(m["match_date"]) >= today_str]
        
        if upcoming_matches_data:
            match_options = {f"{m['match_date']} - {m['location']}": m for m in upcoming_matches_data}
            selected_match_label = st.selectbox("Maç Seçin:", list(match_options.keys()), key="upcoming_select")
            selected_match = match_options[selected_match_label]
            m_id = selected_match["id"]
            
            # Maçın Oyuncu Kadrosunu Çek
            players_res = supabase.table("match_players").select("user_id, profiles(full_name)").eq("match_id", m_id).execute()
            player_names = [get_profile_name(p.get("profiles")) for p in players_res.data]
            
            if not player_names:
                player_names = ["Oyuncu Bulunamadı"]

            # Onaylanmış Kadro Var Mı?
            approved_draft = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("is_approved", True).execute()
            
            if approved_draft.data:
                st.success("🏆 **BU MAÇIN RESMİ KADROSU ADMİN TARAFINDAN ONAYLANDI!**")
                official = approved_draft.data[0]
                render_pitch(official["team_a"], official["team_b"])
            else:
                st.info("💡 Resmi kadro henüz onaylanmadı. Aşağıdan kendi kadro önerinizi oluşturabilirsiniz.")
                
                # Kullanıcının Mevcut Taslağı Var Mı?
                user_draft_res = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("user_id", user_id).execute()
                saved_draft = user_draft_res.data[0] if user_draft_res.data else None
                
                # Admin İçin Gelen Önerileri İnceleme Paneli
                if group["is_admin"]:
                    with st.expander("👑 Admin Özel: Gelen Kadro Önerilerini İncele & Onayla"):
                        all_drafts = supabase.table("match_squad_drafts").select("*, profiles(full_name)").eq("match_id", m_id).execute()
                        if all_drafts.data:
                            for d in all_drafts.data:
                                creator = get_profile_name(d.get("profiles"))
                                st.write(f"**Öneri Sahibi:** {creator}")
                                render_pitch(d["team_a"], d["team_b"])
                                if st.button(f"Bu Kadroyu Resmi Kadro Yap ({creator})", key=f"appr_{d['id']}"):
                                    supabase.table("match_squad_drafts").update({"is_approved": False}).eq("match_id", m_id).execute()
                                    supabase.table("match_squad_drafts").update({"is_approved": True}).eq("id", d["id"]).execute()
                                    st.success("Resmi kadro onaylandı!")
                                    st.rerun()
                                st.divider()
                        else:
                            st.caption("Henüz herhangi bir kullanıcı kadro önerisi göndermedi.")

                st.markdown("### 🛠️ Kendi Kadro Taslağını Kur")
                
                # --- BERABER / AYRI OYNAMA ŞARTLARI ---
                st.markdown("#### 1️⃣ Oyuncu İlişki Şartları")
                col_to, col_sep = st.columns(2)
                
                init_tog = saved_draft.get("together_pairs", []) if saved_draft else []
                init_sep = saved_draft.get("separate_pairs", []) if saved_draft else []
                
                with col_to:
                    st.caption("🤝 Beraber Oynaması İstenen İkililer")
                    tog_count = st.number_input("İkili Sayısı", min_value=0, max_value=5, value=len(init_tog), key="tog_c")
                    together_pairs = []
                    for i in range(tog_count):
                        def_a = init_tog[i][0] if i < len(init_tog) else player_names[0]
                        def_b = init_tog[i][1] if i < len(init_tog) else (player_names[1] if len(player_names)>1 else player_names[0])
                        p1 = st.selectbox(f"Birlikte {i+1} - Oyuncu 1", player_names, index=player_names.index(def_a) if def_a in player_names else 0, key=f"tog_1_{i}")
                        p2 = st.selectbox(f"Birlikte {i+1} - Oyuncu 2", player_names, index=player_names.index(def_b) if def_b in player_names else 0, key=f"tog_2_{i}")
                        together_pairs.append([p1, p2])
                        
                with col_sep:
                    st.caption("⚔️ Ayrı Takımlarda Oynaması İstenen İkililer")
                    sep_count = st.number_input("İkili Sayısı", min_value=0, max_value=5, value=len(init_sep), key="sep_c")
                    separate_pairs = []
                    for i in range(sep_count):
                        def_a = init_sep[i][0] if i < len(init_sep) else player_names[0]
                        def_b = init_sep[i][1] if i < len(init_sep) else (player_names[1] if len(player_names)>1 else player_names[0])
                        p1 = st.selectbox(f"Ayrı {i+1} - Oyuncu 1", player_names, index=player_names.index(def_a) if def_a in player_names else 0, key=f"sep_1_{i}")
                        p2 = st.selectbox(f"Ayrı {i+1} - Oyuncu 2", player_names, index=player_names.index(def_b) if def_b in player_names else 0, key=f"sep_2_{i}")
                        separate_pairs.append([p1, p2])

                # Kadro Durumu State
                if "current_team_a" not in st.session_state:
                    st.session_state.current_team_a = saved_draft["team_a"] if saved_draft else player_names[:len(player_names)//2]
                if "current_team_b" not in st.session_state:
                    st.session_state.current_team_b = saved_draft["team_b"] if saved_draft else player_names[len(player_names)//2:]

                st.markdown("#### 2️⃣ Kadro Oluşturma Yöntemi")
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    if st.button("🎲 Şartlara Göre Rastgele Kadro Kur"):
                        plist = player_names.copy()
                        random.shuffle(plist)
                        half = len(plist) // 2
                        t_a, t_b = plist[:half], plist[half:]
                        
                        for p1, p2 in together_pairs:
                            if p1 in t_a and p2 in t_b:
                                t_b.remove(p2); t_a.append(p2)
                            elif p1 in t_b and p2 in t_a:
                                t_a.remove(p2); t_b.append(p2)
                        
                        st.session_state.current_team_a = t_a
                        st.session_state.current_team_b = t_b
                        st.rerun()

                st.markdown("#### ✍️ Manuel Kadro Düzenleme")
                man_a = st.multiselect("🔵 A Takımı Oyuncuları", options=player_names, default=st.session_state.current_team_a, key="man_select_a")
                man_b = [p for p in player_names if p not in man_a]
                
                st.session_state.current_team_a = man_a
                st.session_state.current_team_b = man_b
                
                st.markdown("#### ⚽ Canlı Önizleme (Futbol Sahası)")
                render_pitch(st.session_state.current_team_a, st.session_state.current_team_b)

                st.write("---")
                save_col, send_col = st.columns(2)
                
                with save_col:
                    if st.button("💾 Taslağı Kaydet (Çıkıp Sonra Devam Et)", use_container_width=True):
                        data = {
                            "match_id": m_id,
                            "user_id": user_id,
                            "team_a": st.session_state.current_team_a,
                            "team_b": st.session_state.current_team_b,
                            "together_pairs": together_pairs,
                            "separate_pairs": separate_pairs
                        }
                        supabase.table("match_squad_drafts").upsert(data, on_conflict="match_id, user_id").execute()
                        st.success("Taslağınız kaydedildi! Sayfayı kapatsanız da buradan devam edebilirsiniz.")
                
                with send_col:
                    btn_label = "📢 İlan Et & Resmi Kadro Yap" if group["is_admin"] else "📨 Admine Kadro Önerisini Gönder"
                    if st.button(btn_label, use_container_width=True):
                        data = {
                            "match_id": m_id,
                            "user_id": user_id,
                            "team_a": st.session_state.current_team_a,
                            "team_b": st.session_state.current_team_b,
                            "together_pairs": together_pairs,
                            "separate_pairs": separate_pairs,
                            "is_approved": True if group["is_admin"] else False
                        }
                        supabase.table("match_squad_drafts").upsert(data, on_conflict="match_id, user_id").execute()
                        if group["is_admin"]:
                            st.success("Kadro resmi olarak ilan edildi!")
                        else:
                            st.success("Kadro öneriniz admine iletildi!")
                        st.rerun()
        else:
            st.info("Planlanmış gelecek bir maç bulunmuyor. 'Maç Planla' sekmesinden yeni bir maç oluşturabilirsiniz.")

    # =========================================================
    # TAB 2: YENİ MAÇ OLUŞTUR
    # =========================================================
    with tab_create:
        st.subheader("Yeni Maç Planla")
        if group["is_admin"]:
            match_date = st.date_input("Maç Tarihi")
            location = st.text_input("Halı Saha / Saha Adı", value="Merkez Halı Saha")
            
            members_data = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).execute()
            player_dict = {get_profile_name(m.get("profiles")): m["user_id"] for m in members_data.data}
            
            selected_players = st.multiselect("Kadroya Alınacak Oyuncular", options=list(player_dict.keys()), default=list(player_dict.keys()))
            
            if st.button("Maçı Oluştur"):
                if selected_players:
                    try:
                        match_res = supabase.table("matches").insert({
                            "group_id": group["id"],
                            "match_date": str(match_date),
                            "location": location,
                            "created_by": user_id
                        }).execute()
                        match_id = match_res.data[0]["id"]
                        
                        players_to_insert = [{"match_id": match_id, "user_id": player_dict[p]} for p in selected_players]
                        supabase.table("match_players").insert(players_to_insert).execute()
                        
                        st.success("Maç oluşturuldu! Gelecek Maçlar sekmesinden kadro kurabilirsiniz.")
                    except Exception as e:
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Lütfen en az bir oyuncu seçin.")
        else:
            st.info("Sadece grup adminleri yeni maç oluşturabilir.")

    # =========================================================
    # TAB 3: GEÇMİŞ MAÇLAR
    # =========================================================
    with tab_past:
        st.subheader("Oynanmış Grup Maçları")
        past_matches_data = [m for m in matches_list if str(m["match_date"]) < today_str]
        
        if past_matches_data:
            match_options = {f"{m['match_date']} - {m['location']}": m["id"] for m in past_matches_data}
            selected_match_label = st.selectbox("Bir Geçmiş Maç Seçin:", list(match_options.keys()))
            selected_match_id = match_options[selected_match_label]
            
            players_in_match = supabase.table("match_players").select("user_id, goals, assists, profiles(full_name)").eq("match_id", selected_match_id).execute()
            
            st.write("#### 📊 Maç Performansı")
            table_data = [{"Oyuncu": get_profile_name(p.get("profiles")), "Gol": p["goals"], "Asist": p["assists"]} for p in players_in_match.data]
            st.table(table_data)

            st.write("---")
            user_in_match = [p for p in players_in_match.data if p["user_id"] == user_id]
            if user_in_match:
                curr_p = user_in_match[0]
                col_g, col_a, col_btn = st.columns([1, 1, 1])
                with col_g:
                    my_goals = st.number_input("Attığın Gol", min_value=0, value=curr_p["goals"])
                with col_a:
                    my_assists = st.number_input("Yaptığın Asist", min_value=0, value=curr_p["assists"])
                with col_btn:
                    st.write(" ")
                    st.write(" ")
                    if st.button("İstatistikleri Kaydet"):
                        supabase.table("match_players").update({"goals": my_goals, "assists": my_assists}).eq("match_id", selected_match_id).eq("user_id", user_id).execute()
                        st.success("Güncellendi!")
                        st.rerun()
        else:
            st.info("Henüz geçmiş bir maç bulunmuyor.")

    # =========================================================
    # TAB 4: PUAN SIRALAMASI
    # =========================================================
    with tab_leaderboard:
        st.subheader("🏆 Genel İstatistikler ve Sıralama")
        all_players = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).execute()
        
        leaderboard = []
        for p in all_players.data:
            p_id = p["user_id"]
            p_name = get_profile_name(p.get("profiles"))
            
            stats = supabase.table("match_players").select("goals, assists").eq("user_id", p_id).execute()
            tot_goals = sum([item["goals"] for item in stats.data]) if stats.data else 0
            tot_assists = sum([item["assists"] for item in stats.data]) if stats.data else 0
            
            leaderboard.append({"Oyuncu": p_name, "Toplam Gol": tot_goals, "Toplam Asist": tot_assists})
            
        leaderboard = sorted(leaderboard, key=lambda x: (x["Toplam Gol"], x["Toplam Asist"]), reverse=True)
        st.table(leaderboard)

# ---------------------------------------------------------
# Ana Çalıştırma Mantığı
# ---------------------------------------------------------
if st.session_state.user is None:
    auth_screen()
else:
    st.sidebar.write(f"👤 **{st.session_state.user.email}**")
    if st.sidebar.button("Çıkış Yap"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.selected_group = None
        st.rerun()

    if st.session_state.selected_group is None:
        main_dashboard()
    else:
        group_detail()
