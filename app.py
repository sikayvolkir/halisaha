import streamlit as st
from supabase import create_client, Client
import random
from datetime import date

# ---------------------------------------------------------
# Sayfa Konfigürasyonu & Tema
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
    .comment-card {
        background-color: #161b22;
        border-left: 3px solid #238636;
        padding: 10px 15px;
        margin-bottom: 10px;
        border-radius: 4px;
    }

    /* Tamamen Saha İçi Yapısı */
    .pitch-container {
        background-color: #2e7d32;
        background-image: linear-gradient(to right, rgba(255,255,255,0.15) 50%, transparent 50%);
        background-size: 80px 100%;
        border: 4px solid #ffffff;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        position: relative;
        min-height: 350px;
        display: flex;
        justify-content: space-between;
    }
    .pitch-half {
        width: 48%;
        z-index: 2;
    }
    .pitch-center-line {
        position: absolute;
        left: 50%;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: rgba(255, 255, 255, 0.7);
        z-index: 1;
    }
    .pitch-team-title-a, .pitch-team-title-b {
        color: #ffffff;
        font-weight: bold;
        font-size: 1.2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        margin-bottom: 15px;
    }
    .player-chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .player-chip {
        background-color: #1f6feb;
        color: white;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.5);
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

# Session State Tanımlamaları
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_group" not in st.session_state:
    st.session_state.selected_group = None
if "together_count" not in st.session_state:
    st.session_state.together_count = 1
if "separate_count" not in st.session_state:
    st.session_state.separate_count = 1

# Oturumun Yenilemelerde Kalıcı Olması
try:
    session = supabase.auth.get_session()
    if session and session.user:
        st.session_state.user = session.user
except Exception:
    pass

def get_player_display_name(p_item):
    if p_item.get("custom_name"):
        return p_item["custom_name"]
    profile = p_item.get("profiles")
    if isinstance(profile, dict):
        return profile.get("full_name", "Bilinmeyen Oyuncu")
    elif isinstance(profile, list) and len(profile) > 0:
        return profile[0].get("full_name", "Bilinmeyen Oyuncu")
    return "Bilinmeyen Oyuncu"

def get_profile_name(profile_data):
    if isinstance(profile_data, dict):
        return profile_data.get("full_name", "Bilinmeyen Oyuncu")
    elif isinstance(profile_data, list) and len(profile_data) > 0:
        return profile_data[0].get("full_name", "Bilinmeyen Oyuncu")
    return "Bilinmeyen Oyuncu"

# ---------------------------------------------------------
# Davet & Derin Bağlantı (Deep Link) Kontrolü
# ---------------------------------------------------------
def handle_invite():
    query_params = st.query_params
    if "group_id" in query_params:
        target_group_id = query_params["group_id"]
        target_match_id = query_params.get("match_id", None)
        
        if st.session_state.user is not None:
            user_id = st.session_state.user.id
            member_check = supabase.table("group_members").select("*").eq("group_id", target_group_id).eq("user_id", user_id).execute()
            
            if member_check.data:
                group_data = supabase.table("groups").select("id, name").eq("id", target_group_id).execute()
                if group_data.data:
                    g = group_data.data[0]
                    st.session_state.selected_group = {
                        "id": g["id"],
                        "name": g["name"],
                        "is_admin": member_check.data[0]["is_admin"],
                        "is_left": member_check.data[0].get("is_left", False),
                        "target_match_id": target_match_id
                    }
                    st.query_params.clear()
                    st.rerun()
            else:
                try:
                    supabase.table("group_join_requests").insert({
                        "group_id": target_group_id,
                        "user_id": user_id
                    }).execute()
                    st.toast("🎉 Davet linki ile katılım isteğiniz gruba iletildi!", icon="✅")
                except Exception:
                    pass
                st.query_params.clear()

# ---------------------------------------------------------
# Kimlik Doğrulama Ekranı
# ---------------------------------------------------------
def auth_screen():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    
    if "group_id" in st.query_params:
        st.info("👋 Bir gruba katılmak veya maçı görüntülemek için davet edildiniz! Lütfen giriş yapın veya kayıt olun.")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        st.subheader("Giriş Yap")
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-Posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_password")
            submit_login = st.form_submit_button("Giriş Yap (Enter)", use_container_width=True)
            
            if submit_login:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.success("Giriş başarılı!")
                    handle_invite()
                    st.rerun()
                except Exception as e:
                    st.error(f"Giriş başarısız: {e}")

    with tab2:
        st.subheader("Yeni Hesap Oluştur")
        with st.form("register_form", clear_on_submit=False):
            full_name = st.text_input("Ad Soyad", key="reg_name")
            email = st.text_input("E-Posta", key="reg_email")
            password = st.text_input("Şifre (En az 6 karakter)", type="password", key="reg_password")
            submit_reg = st.form_submit_button("Kayıt Ol (Enter)", use_container_width=True)
            
            if submit_reg:
                if not full_name.strip():
                    st.warning("Lütfen adınızı ve soyadınızı girin.")
                else:
                    try:
                        res = supabase.auth.sign_up({
                            "email": email,
                            "password": password,
                            "options": {"data": {"full_name": full_name}}
                        })
                        st.session_state.user = res.user
                        st.success("Kayıt başarılı!")
                        handle_invite()
                        st.rerun()
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
        memberships = supabase.table("group_members").select("group_id, is_admin, is_left, groups(id, name)").eq("user_id", user_id).execute()
        
        if memberships.data:
            for item in memberships.data:
                group = item.get("groups")
                if not group:
                    continue
                is_admin = item["is_admin"]
                is_left = item.get("is_left", False)
                
                c_title, c_menu = st.columns([5, 1])
                
                with c_title:
                    btn_label = f"⚽ {group['name']} {'⭐ (Admin)' if is_admin else ''} {'🔒 (Eski Üye - Salt Okunur)' if is_left else ''}"
                    if st.button(btn_label, key=f"group_click_{group['id']}", use_container_width=True):
                        st.session_state.selected_group = {
                            "id": group["id"],
                            "name": group["name"],
                            "is_admin": is_admin,
                            "is_left": is_left
                        }
                        st.rerun()

                with c_menu:
                    with st.popover("⋮"):
                        if not is_left:
                            if st.button("🚪 Gruptan Çık", key=f"leave_{group['id']}"):
                                supabase.table("group_members").update({"is_left": True}).eq("group_id", group["id"]).eq("user_id", user_id).execute()
                                st.success("Gruptan çıkıldı. Geçmiş maçları inceleyebilirsiniz.")
                                st.rerun()
                        if st.button("🗑️ Grubu Sil", key=f"del_{group['id']}"):
                            supabase.table("group_members").delete().eq("group_id", group["id"]).eq("user_id", user_id).execute()
                            st.success("Grup listenizden kaldırıldı.")
                            st.rerun()
                st.divider()
        else:
            st.info("Henüz herhangi bir gruba dahil değilsiniz.")

    with col2:
        st.subheader("Yeni Grup Oluştur")
        with st.form("create_group_form", clear_on_submit=True):
            new_group_name = st.text_input("Grup Adı")
            submit_group = st.form_submit_button("Grubu Kur (Enter)", use_container_width=True)
            if submit_group:
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
                            "is_admin": True,
                            "is_left": False
                        }).execute()
                        st.success("Grup başarıyla oluşturuldu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Grup oluşturulurken hata: {e}")
                else:
                    st.warning("Lütfen bir grup adı girin.")

# ---------------------------------------------------------
# Sahada Kadro Gösterme Bileşeni
# ---------------------------------------------------------
def render_pitch(team_a, team_b):
    chips_a = "".join([f"<span class='player-chip'>{p}</span>" for p in team_a]) if team_a else "<em style='color:rgba(255,255,255,0.7);'>Henüz oyuncu eklenmedi</em>"
    chips_b = "".join([f"<span class='player-chip player-chip-b'>{p}</span>" for p in team_b]) if team_b else "<em style='color:rgba(255,255,255,0.7);'>Henüz oyuncu eklenmedi</em>"
    
    pitch_html = f"""
    <div class="pitch-container">
        <div class="pitch-center-line"></div>
        <div class="pitch-half">
            <div class="pitch-team-title-a">🔵 A Takımı</div>
            <div class="player-chip-container">
                {chips_a}
            </div>
        </div>
        <div class="pitch-half">
            <div class="pitch-team-title-b">🔴 B Takımı</div>
            <div class="player-chip-container">
                {chips_b}
            </div>
        </div>
    </div>
    """
    st.markdown(pitch_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# Grup Detay Sayfası
# ---------------------------------------------------------
def group_detail():
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    is_left = group.get("is_left", False)
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)
    if is_left:
        st.warning("🔒 Bu gruptan ayrıldığınız için verileri yalnızca görüntüleyebilirsiniz. Yeni kadro kuramaz veya değişiklik yapamazsınız.")

    tabs_list = ["📅 Gelecek Maçlar & Kadrolar"]
    if not is_left:
        tabs_list.append("➕ Maç Planla")
        if group["is_admin"]:
            tabs_list.append("➕ Dışarıdan Oyuncu Ekle (Admin)")
            
    tabs_list.extend(["👥 Grup Üyeleri & İstekler", "📜 Geçmiş Maçlar", "🏆 Puan Sıralaması"])

    tabs = st.tabs(tabs_list)
    
    tab_upcoming = tabs[0]
    
    idx = 1
    tab_create = None
    tab_custom_player = None
    
    if not is_left:
        tab_create = tabs[idx]
        idx += 1
        if group["is_admin"]:
            tab_custom_player = tabs[idx]
            idx += 1

    tab_members = tabs[idx]
    tab_past = tabs[idx+1]
    tab_leaderboard = tabs[idx+2]
    
    today_str = str(date.today())
    all_matches = supabase.table("matches").select("*").eq("group_id", group["id"]).execute()
    matches_list = all_matches.data if all_matches.data else []

    # =========================================================
    # TAB 1: GELECEK MAÇLAR & KADRO KURMA
    # =========================================================
    with tab_upcoming:
        st.subheader("📅 Gelecek Maçlar ve Kadro Planlaması")
        upcoming_matches_data = [m for m in matches_list if str(m["match_date"]) >= today_str]
        
        if upcoming_matches_data:
            match_options = {f"{m['match_date']} - {m['location']}": m for m in upcoming_matches_data}
            
            # Direct link ile bir maça girilmişse onu varsayılan yap
            target_m_id = group.get("target_match_id")
            default_index = 0
            match_keys = list(match_options.keys())
            if target_m_id:
                for i, (label, m_data) in enumerate(match_options.items()):
                    if m_data["id"] == target_m_id:
                        default_index = i
                        break
            
            selected_match_label = st.selectbox("Maç Seçin:", match_keys, index=default_index, key="upcoming_select")
            selected_match = match_options[selected_match_label]
            m_id = selected_match["id"]
            
            # --- BU MAÇIN DOĞRUDAN PAYLAŞIM LİNKİ ---
            base_url = "https://halisaha-takip.streamlit.app"
            direct_match_link = f"{base_url}/?group_id={group['id']}&match_id={m_id}"
            with st.popover("🔗 Bu Maçın Linkini Paylaş"):
                st.write("Bu bağlantıyı paylaşarak arkadaşlarınızın doğrudan bu maçın kadro planlamasına gelmesini sağlayabilirsiniz:")
                st.code(direct_match_link, language="text")
            st.divider()
            # ----------------------------------------

            players_res = supabase.table("match_players").select("user_id, custom_name, profiles(full_name)").eq("match_id", m_id).execute()
            player_names = [get_player_display_name(p) for p in players_res.data]
            if not player_names:
                player_names = ["Oyuncu Bulunamadı"]

            approved_draft = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("is_approved", True).execute()
            
            if approved_draft.data:
                st.success("🏆 **BU MAÇIN RESMİ KADROSU ADMİN TARAFINDAN ONAYLANDI!**")
                official = approved_draft.data[0]
                render_pitch(official["team_a"], official["team_b"])
            else:
                st.info("💡 Resmi kadro henüz onaylanmadı.")
                
                user_draft_res = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("user_id", user_id).execute()
                saved_draft = user_draft_res.data[0] if user_draft_res.data else None
                
                if group["is_admin"] and not is_left:
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

                if not is_left:
                    st.markdown("### 🛠️ Kendi Kadro Taslağını Kur")
                    
                    st.markdown("#### 1️⃣ Oyuncu İlişki Şartları")
                    col_to, col_sep = st.columns(2)
                    
                    together_pairs = []
                    with col_to:
                        st.caption("🤝 Beraber Oynaması İstenen İkililer")
                        for i in range(st.session_state.together_count):
                            c1, c2 = st.columns(2)
                            p1 = c1.selectbox(f"Birlikte #{i+1} Oyuncu A", player_names, key=f"tog_a_{i}")
                            p2 = c2.selectbox(f"Birlikte #{i+1} Oyuncu B", player_names, key=f"tog_b_{i}")
                            together_pairs.append([p1, p2])
                        if st.button("➕ Yeni Beraber Oynayacak İkili Ekle"):
                            st.session_state.together_count += 1
                            st.rerun()

                    separate_pairs = []
                    with col_sep:
                        st.caption("⚔️ Ayrı Takımlarda Oynaması İstenen İkililer")
                        for i in range(st.session_state.separate_count):
                            c1, c2 = st.columns(2)
                            p1 = c1.selectbox(f"Ayrı #{i+1} Oyuncu A", player_names, key=f"sep_a_{i}")
                            p2 = c2.selectbox(f"Ayrı #{i+1} Oyuncu B", player_names, key=f"sep_b_{i}")
                            separate_pairs.append([p1, p2])
                        if st.button("➕ Yeni Ayrı Oynayacak İkili Ekle"):
                            st.session_state.separate_count += 1
                            st.rerun()

                    if "current_team_a" not in st.session_state:
                        st.session_state.current_team_a = saved_draft["team_a"] if saved_draft else player_names[:len(player_names)//2]
                    if "current_team_b" not in st.session_state:
                        st.session_state.current_team_b = saved_draft["team_b"] if saved_draft else player_names[len(player_names)//2:]

                    st.markdown("#### 2️⃣ Kadro Oluşturma Yöntemi")
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

                    st.markdown("#### ✍️ Yan Yana Manuel Kadro Seçimi")
                    man_col_a, man_col_b = st.columns(2)
                    
                    with man_col_a:
                        selected_a = st.multiselect(
                            "🔵 A Takımı Oyuncuları", 
                            options=player_names, 
                            default=[p for p in st.session_state.current_team_a if p in player_names],
                            key=f"man_select_a_side_{m_id}"
                        )
                    
                    remaining_for_b = [p for p in player_names if p not in selected_a]
                    
                    with man_col_b:
                        selected_b = st.multiselect(
                            "🔴 B Takımı Oyuncuları", 
                            options=remaining_for_b, 
                            default=[p for p in st.session_state.current_team_b if p in remaining_for_b],
                            key=f"man_select_b_side_{m_id}"
                        )

                    st.session_state.current_team_a = selected_a
                    st.session_state.current_team_b = selected_b
                    
                    st.markdown("#### 🏟️ Canlı Kadro Görünümü")
                    render_pitch(st.session_state.current_team_a, st.session_state.current_team_b)

                    st.write("---")
                    save_col, send_col = st.columns(2)
                    
                    with save_col:
                        if st.button("💾 Taslağı Kaydet", use_container_width=True):
                            data = {
                                "match_id": m_id,
                                "user_id": user_id,
                                "team_a": st.session_state.current_team_a,
                                "team_b": st.session_state.current_team_b,
                                "together_pairs": together_pairs,
                                "separate_pairs": separate_pairs
                            }
                            supabase.table("match_squad_drafts").upsert(data, on_conflict="match_id, user_id").execute()
                            st.success("Taslağınız kaydedildi!")
                    
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
                            st.success("İşlem başarılı!")
                            st.rerun()
        else:
            st.info("Planlanmış gelecek bir maç bulunmuyor.")

    # =========================================================
    # TAB 2: YENİ MAÇ OLUŞTUR
    # =========================================================
    if tab_create:
        with tab_create:
            if group["is_admin"]:
                st.subheader("➕ Yeni Maç Planla")
                match_date = st.date_input("Maç Tarihi")
                location = st.text_input("Halı Saha / Saha Adı", value="Merkez Halı Saha")
                
                members_data = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).eq("is_left", False).execute()
                player_dict = {get_profile_name(m.get("profiles")): m["user_id"] for m in members_data.data}
                
                selected_players = st.multiselect("Gruptan Kadroya Alınacak Oyuncular", options=list(player_dict.keys()), default=list(player_dict.keys()))
                
                if st.button("Maçı Oluştur", use_container_width=True):
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
                            
                            st.success("Maç başarıyla oluşturuldu!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")

    # =========================================================
    # TAB 3: DIŞARIDAN OYUNCU EKLEME (ADMİN)
    # =========================================================
    if group["is_admin"] and tab_custom_player:
        with tab_custom_player:
            st.subheader("👤 Dışarıdan / Kayıtsız Oyuncu Ekle (Sadece Admin)")
            
            upcoming_matches = [m for m in matches_list if str(m["match_date"]) >= today_str]
            if upcoming_matches:
                m_opt = {f"{m['match_date']} - {m['location']}": m["id"] for m in upcoming_matches}
                sel_m_id = st.selectbox("Oyuncu Eklenecek Maçı Seçin:", list(m_opt.keys()), key="custom_p_match_select")
                
                with st.form(key="add_custom_player_form", clear_on_submit=True):
                    custom_name_val = st.text_input("Dışarıdan Gelecek Oyuncunun Adı Soyadı:", placeholder="İsim yazın ve Enter'a basın...")
                    submit_custom_p = st.form_submit_button("➕ Oyuncuyu Kadroya Dahil Et (Enter)")
                    
                    if submit_custom_p:
                        if custom_name_val.strip():
                            supabase.table("match_players").insert({
                                "match_id": m_opt[sel_m_id],
                                "custom_name": custom_name_val.strip()
                            }).execute()
                            st.success(f"✅ '{custom_name_val.strip()}' maça başarıyla eklendi!")
                            st.rerun()
                        else:
                            st.warning("Lütfen bir isim girin.")

                st.write("---")
                st.subheader("📋 Bu Maçın Mevcut Kadrosu")
                curr_players = supabase.table("match_players").select("user_id, custom_name, profiles(full_name)").eq("match_id", m_opt[sel_m_id]).execute()
                
                if curr_players.data:
                    for i, p in enumerate(curr_players.data, 1):
                        p_name = get_player_display_name(p)
                        tag = " (Kayıtsız Dış Oyuncu)" if p.get("custom_name") else " (Grup Üyesi)"
                        st.write(f"**{i}.** {p_name} <small style='color:#8b949e;'>{tag}</small>", unsafe_allow_html=True)
                else:
                    st.caption("Bu maça henüz oyuncu eklenmedi.")

    # =========================================================
    # TAB: GRUP ÜYELERİ & KATILIM İSTEKLERİ
    # =========================================================
    with tab_members:
        st.subheader("🔗 Gruba Davet Linki")
        base_url = "https://halisaha-takip.streamlit.app"
        invite_link = f"{base_url}/?group_id={group['id']}"
        st.code(invite_link, language="text")
        st.caption("Bu bağlantıyı paylaşarak arkadaşlarınızı gruba davet edebilirsiniz (Mevcut üyeler doğrudan gruba girer).")
        st.divider()

        st.subheader("👥 Grup Üyeleri")
        members = supabase.table("group_members").select("is_admin, is_left, profiles(full_name)").eq("group_id", group["id"]).execute()
        
        for m in members.data:
            name = get_profile_name(m.get("profiles"))
            status = " (Ayrıldı)" if m.get("is_left") else ""
            role = "⭐ Admin" if m["is_admin"] else "🏃 Oyuncu"
            st.write(f"- **{name}** ({role}){status}")
            
        if group["is_admin"] and not is_left:
            st.divider()
            st.subheader("🔔 Bekleyen Katılım İstekleri")
            requests = supabase.table("group_join_requests").select("id, user_id, profiles(full_name)").eq("group_id", group["id"]).eq("status", "pending").execute()
            
            if requests.data:
                for req in requests.data:
                    u_name = get_profile_name(req.get("profiles"))
                    col_req_1, col_req_2, col_req_3 = st.columns([2, 1, 1])
                    col_req_1.write(f"**{u_name}** gruba katılmak istiyor.")
                    
                    if col_req_2.button("✅ Onayla", key=f"acc_{req['id']}"):
                        supabase.table("group_members").insert({"group_id": group["id"], "user_id": req["user_id"], "is_admin": False, "is_left": False}).execute()
                        supabase.table("group_join_requests").update({"status": "approved"}).eq("id", req["id"]).execute()
                        st.success(f"{u_name} gruba eklendi!")
                        st.rerun()
                        
                    if col_req_3.button("❌ Reddet", key=f"rej_{req['id']}"):
                        supabase.table("group_join_requests").update({"status": "rejected"}).eq("id", req["id"]).execute()
                        st.info(f"{u_name} isteği reddedildi.")
                        st.rerun()

    # =========================================================
    # TAB: GEÇMİŞ MAÇLAR & YORUMLAR
    # =========================================================
    with tab_past:
        st.subheader("📜 Oynanmış Geçmiş Maçlar")
        past_matches_data = [m for m in matches_list if str(m["match_date"]) < today_str]
        
        if past_matches_data:
            match_options = {f"{m['match_date']} - {m['location']}": m["id"] for m in past_matches_data}
            selected_match_label = st.selectbox("Bir Geçmiş Maç Seçin:", list(match_options.keys()))
            selected_match_id = match_options[selected_match_label]
            
            players_in_match = supabase.table("match_players").select("user_id, custom_name, goals, assists, profiles(full_name)").eq("match_id", selected_match_id).execute()
            
            st.write("#### 📊 Maç Performansı & İstatistikler")
            table_data = [{"Oyuncu": get_player_display_name(p), "Gol": p.get("goals", 0), "Asist": p.get("assists", 0)} for p in players_in_match.data]
            st.table(table_data)

            st.write("---")
            st.subheader("💬 Geçmiş Maç Yorumları ve Medya Paylaşımı")
            
            if not is_left:
                with st.form(key=f"comment_form_{selected_match_id}", clear_on_submit=True):
                    comment_text = st.text_area("Yorumunuz / Maç Değerlendirmesi", placeholder="Maç hakkında duygu ve düşüncelerinizi yazın...")
                    media_url = st.text_input("Medya / Görsel Bağlantısı (Opsiyonel)", placeholder="https://...")
                    submit_comment = st.form_submit_button("💬 Yorum Yap (Enter)")
                    
                    if submit_comment:
                        if comment_text.strip():
                            try:
                                supabase.table("match_comments").insert({
                                    "match_id": selected_match_id,
                                    "user_id": user_id,
                                    "comment": comment_text.strip(),
                                    "media_url": media_url.strip() if media_url else None
                                }).execute()
                                st.success("Yorumunuz eklendi!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Yorum eklenirken hata oluştu: {e}")
                        else:
                            st.warning("Lütfen bir yorum metni girin.")

            st.write("---")
            st.markdown("#### 💬 Yapılan Yorumlar")
            
            comments_res = supabase.table("match_comments") \
                .select("id, comment, media_url, created_at, profiles(full_name)") \
                .eq("match_id", selected_match_id) \
                .order("created_at", desc=True) \
                .execute()
                
            if comments_res.data:
                for c in comments_res.data:
                    author_name = get_profile_name(c.get("profiles"))
                    st.markdown(f"""
                    <div class="comment-card">
                        <strong>👤 {author_name}</strong> <small style='color:#8b949e;'>({c.get('created_at', '')[:10]})</small><br>
                        {c['comment']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if c.get("media_url"):
                        st.image(c["media_url"], use_container_width=True)
            else:
                st.caption("Bu maç için henüz yorum yapılmamış.")
        else:
            st.info("Oynanmış geçmiş bir maç bulunmuyor.")

    # =========================================================
    # TAB: PUAN SIRALAMASI & İSTATİSTİKLER
    # =========================================================
    with tab_leaderboard:
        st.subheader("🏆 Grup Puan ve Performans Sıralaması")
        
        past_match_ids = [m["id"] for m in matches_list if str(m["match_date"]) < today_str]
        
        if past_match_ids:
            stats_res = supabase.table("match_players") \
                .select("user_id, custom_name, goals, assists, profiles(full_name)") \
                .in_("match_id", past_match_ids) \
                .execute()
                
            if stats_res.data:
                leaderboard = {}
                for row in stats_res.data:
                    name = get_player_display_name(row)
                    goals = row.get("goals") or 0
                    assists = row.get("assists") or 0
                    
                    if name not in leaderboard:
                        leaderboard[name] = {"Maç": 0, "Gol": 0, "Asist": 0, "Toplam Skora Katkı": 0}
                    
                    leaderboard[name]["Maç"] += 1
                    leaderboard[name]["Gol"] += goals
                    leaderboard[name]["Asist"] += assists
                    leaderboard[name]["Toplam Skora Katkı"] += (goals + assists)
                
                sorted_leaderboard = sorted(
                    [{"Oyuncu": k, **v} for k, v in leaderboard.items()],
                    key=lambda x: x["Toplam Skora Katkı"],
                    reverse=True
                )
                
                st.table(sorted_leaderboard)
            else:
                st.info("Henüz girilmiş maç istatistiği bulunmuyor.")
        else:
            st.info("İstatistik oluşturmak için henüz tamamlanmış bir maç yok.")

# ---------------------------------------------------------
# Ana Akış Yönlendirmesi (Main Loop)
# ---------------------------------------------------------
def main():
    if st.session_state.user is None:
        auth_screen()
    else:
        handle_invite()
        
        if st.session_state.selected_group is None:
            main_dashboard()
        else:
            group_detail()

if __name__ == "__main__":
    main()
