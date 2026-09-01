import streamlit as st
from supabase import create_client, Client
import random
from datetime import date
import uuid

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
    .chat-bubble {
        background-color: #161b22;
        border-left: 4px solid #238636;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    .chat-user {
        font-weight: bold;
        color: #58a6ff;
        font-size: 0.9rem;
    }
    .chat-time {
        color: #8b949e;
        font-size: 0.75rem;
        float: right;
    }

    /* Saha İçi Yapısı */
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
    .player-chip {
        background-color: #1f6feb;
        color: white;
        padding: 8px 14px;
        border-radius: 20px;
        font-size: 0.95rem;
        font-weight: 600;
        box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.5);
        display: inline-block;
        margin: 3px;
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
if "pending_group_id" not in st.session_state:
    st.session_state.pending_group_id = None
if "together_count" not in st.session_state:
    st.session_state.together_count = 1
if "separate_count" not in st.session_state:
    st.session_state.separate_count = 1

if "group_id" in st.query_params:
    st.session_state.pending_group_id = st.query_params["group_id"]

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
# SOHBET BİLEŞENİ (Geçmiş ve Gelecek Maçlar İçin)
# ---------------------------------------------------------
def render_match_chat(match_id, user_id, is_left):
    st.markdown("---")
    st.write("### 💬 Maç Sohbeti & Medya Paylaşımı")
    
    # Mesajları Getir
    msg_res = supabase.table("match_messages").select("*, profiles(full_name)").eq("match_id", match_id).order("created_at", desc=False).execute()
    
    chat_container = st.container()
    with chat_container:
        if msg_res.data:
            for msg in msg_res.data:
                author = get_profile_name(msg.get("profiles"))
                time_str = msg.get("created_at", "")[:16].replace("T", " ")
                
                st.markdown(f"""
                <div class="chat-bubble">
                    <span class="chat-user">{author}</span> <span class="chat-time">{time_str}</span><br/>
                    <div style="margin-top:5px;">{msg.get('message') or ''}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Resim/Video Varsa Göster
                if msg.get("media_url"):
                    if msg.get("media_type") == "image":
                        st.image(msg["media_url"], use_column_width=True)
                    elif msg.get("media_type") == "video":
                        st.video(msg["media_url"])
        else:
            st.caption("Henüz mesaj yok. İlk mesajı sen yaz!")

    # Mesaj Gönderme Alanı
    if not is_left:
        with st.form(key=f"chat_form_{match_id}", clear_on_submit=True):
            user_msg = st.text_input("Mesajınız:", placeholder="Sohbete bir şeyler yazın...")
            uploaded_file = st.file_uploader("Fotoğraf / Video Ekle", type=["jpg", "jpeg", "png", "mp4", "mov"])
            submit_btn = st.form_submit_button("📤 Gönder")

            if submit_btn:
                if user_msg.strip() or uploaded_file:
                    media_url = None
                    media_type = None

                    # Medya Yükleme
                    if uploaded_file:
                        file_ext = uploaded_file.name.split(".")[-1].lower()
                        file_path = f"{match_id}/{uuid.uuid4()}.{file_ext}"
                        
                        file_bytes = uploaded_file.read()
                        supabase.storage.from_("match_media").upload(file_path, file_bytes)
                        media_url = supabase.storage.from_("match_media").get_public_url(file_path)
                        
                        if file_ext in ["jpg", "jpeg", "png"]:
                            media_type = "image"
                        elif file_ext in ["mp4", "mov"]:
                            media_type = "video"

                    # Veritabanına Ekle
                    supabase.table("match_messages").insert({
                        "match_id": match_id,
                        "user_id": user_id,
                        "message": user_msg.strip(),
                        "media_url": media_url,
                        "media_type": media_type
                    }).execute()
                    st.rerun()

# ---------------------------------------------------------
# GRUP DAVET ONAY EKRANI
# ---------------------------------------------------------
def render_invite_confirmation_screen():
    group_id = st.session_state.pending_group_id
    user_id = st.session_state.user.id

    group_res = supabase.table("groups").select("id, name").eq("id", group_id).execute()
    if not group_res.data:
        st.error("❌ Davet edildiğiniz grup bulunamadı.")
        if st.button("Ana Sayfaya Git", use_container_width=True):
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()
        return

    group_data = group_res.data[0]
    member_check = supabase.table("group_members").select("*").eq("group_id", group_id).eq("user_id", user_id).execute()
    if member_check.data:
        st.success(f"🎉 **{group_data['name']}** grubunun zaten üyesisiniz!")
        if st.button("Gruba Git", use_container_width=True):
            st.session_state.selected_group = {
                "id": group_data["id"],
                "name": group_data["name"],
                "is_admin": member_check.data[0].get("is_admin", False),
                "is_left": member_check.data[0].get("is_left", False)
            }
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()
        return

    st.markdown("<h2 class='main-title'>⚽ GRUP DAVETİ</h2>", unsafe_allow_html=True)
    st.info(f"**{group_data['name']}** grubuna katılmak üzere davet edildiniz.")

    col_approve, col_reject = st.columns(2)
    with col_approve:
        if st.button("✅ İsteği Admin'e Gönder", use_container_width=True):
            try:
                supabase.table("group_join_requests").insert({"group_id": group_id, "user_id": user_id, "status": "pending"}).execute()
                st.success("Katılım isteğiniz grup adminine iletildi!")
                st.session_state.pending_group_id = None
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

    with col_reject:
        if st.button("❌ Vazgeç", use_container_width=True):
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()

# ---------------------------------------------------------
# AUTH EKRANI
# ---------------------------------------------------------
def auth_screen():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("E-Posta")
            password = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Giriş başarısız: {e}")

    with tab2:
        with st.form("register_form"):
            full_name = st.text_input("Ad Soyad")
            email = st.text_input("E-Posta")
            password = st.text_input("Şifre (En az 6 karakter)", type="password")
            if st.form_submit_button("Kayıt Ol", use_container_width=True):
                if full_name.strip():
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": full_name}}})
                        st.session_state.user = res.user
                        st.success("Kayıt başarılı!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kayıt başarısız: {e}")

# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------
def main_dashboard():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA GRUPLARIM</h1>", unsafe_allow_html=True)
    user_id = st.session_state.user.id
    
    if st.button("🚪 Oturumu Kapat"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.selected_group = None
        st.rerun()

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Dahil Olduğunuz Gruplar")
        memberships = supabase.table("group_members").select("group_id, is_admin, is_left, groups(id, name)").eq("user_id", user_id).execute()
        
        my_group_ids = []
        if memberships.data:
            for item in memberships.data:
                group = item.get("groups")
                if not group: continue
                my_group_ids.append(group["id"])
                
                c_title, c_menu = st.columns([5, 1])
                with c_title:
                    btn_label = f"⚽ {group['name']} {'⭐ (Admin)' if item['is_admin'] else ''}"
                    if st.button(btn_label, key=f"g_click_{group['id']}", use_container_width=True):
                        st.session_state.selected_group = {"id": group["id"], "name": group["name"], "is_admin": item["is_admin"], "is_left": item.get("is_left", False)}
                        st.rerun()

                with c_menu:
                    with st.popover("⋮"):
                        if not item.get("is_left"):
                            if st.button("🚪 Gruptan Çık", key=f"leave_{group['id']}"):
                                supabase.table("group_members").update({"is_left": True}).eq("group_id", group["id"]).eq("user_id", user_id).execute()
                                st.rerun()
        else:
            st.info("Henüz bir gruba dahil değilsiniz.")

        st.subheader("🔍 Grup Ara & Katıl")
        search_query = st.text_input("Grup Adı Ara", key="search_g_input")
        if search_query.strip():
            search_res = supabase.table("groups").select("id, name").ilike("name", f"%{search_query.strip()}%").execute()
            if search_res.data:
                user_requests = supabase.table("group_join_requests").select("group_id, status").eq("user_id", user_id).execute()
                pending_ids = [r["group_id"] for r in user_requests.data if r.get("status") == "pending"]

                for g in search_res.data:
                    if g["id"] in my_group_ids: continue
                    g_col1, g_col2 = st.columns([3, 1])
                    g_col1.write(f"⚽ **{g['name']}**")
                    if g["id"] in pending_ids:
                        g_col2.button("⏳ Beklemede", key=f"req_p_{g['id']}", disabled=True)
                    else:
                        if g_col2.button("➕ İstek Gönder", key=f"req_s_{g['id']}"):
                            supabase.table("group_join_requests").insert({"group_id": g["id"], "user_id": user_id, "status": "pending"}).execute()
                            st.success("İstek gönderildi!")
                            st.rerun()

    with col2:
        st.subheader("Yeni Grup Oluştur")
        with st.form("create_group_form", clear_on_submit=True):
            new_group_name = st.text_input("Grup Adı")
            if st.form_submit_button("Grubu Kur", use_container_width=True):
                if new_group_name.strip():
                    group_res = supabase.table("groups").insert({"name": new_group_name.strip(), "created_by": user_id}).execute()
                    new_g_id = group_res.data[0]["id"]
                    supabase.table("group_members").insert({"group_id": new_g_id, "user_id": user_id, "is_admin": True}).execute()
                    st.success("Grup oluşturuldu!")
                    st.rerun()

# ---------------------------------------------------------
# SAHA BİLEŞENİ
# ---------------------------------------------------------
def render_pitch(team_a, team_b):
    chips_a = "".join([f"<span class='player-chip'>{p}</span>" for p in team_a]) if team_a else "<em>Oyuncu yok</em>"
    chips_b = "".join([f"<span class='player-chip player-chip-b'>{p}</span>" for p in team_b]) if team_b else "<em>Oyuncu yok</em>"
    
    st.markdown(f"""
    <div class="pitch-container">
        <div class="pitch-center-line"></div>
        <div class="pitch-half">
            <div class="pitch-team-title-a">🔵 A Takımı</div>
            <div>{chips_a}</div>
        </div>
        <div class="pitch-half">
            <div class="pitch-team-title-b">🔴 B Takımı</div>
            <div>{chips_b}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# GRUP DETAY SAYFASI
# ---------------------------------------------------------
def group_detail():
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    is_left = group.get("is_left", False)
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)

    tabs_list = ["📅 Gelecek Maçlar & Kadrolar"]
    if not is_left and group["is_admin"]:
        tabs_list.append("➕ Maç Planla")
            
    tabs_list.extend(["👥 Üyeler & İstekler", "📜 Geçmiş Maçlar & Sohbet", "🏆 Puan Sıralaması"])
    tabs = st.tabs(tabs_list)
    
    today_str = str(date.today())
    all_matches = supabase.table("matches").select("*").eq("group_id", group["id"]).execute()
    matches_list = all_matches.data if all_matches.data else []

    # TAB 1: GELECEK MAÇLAR & KATILIM
    with tabs[0]:
        st.subheader("📅 Gelecek Maçlar")
        upcoming = [m for m in matches_list if str(m["match_date"]) >= today_str]
        
        if upcoming:
            m_opt = {f"{m['match_date']} - {m['location']}": m for m in upcoming}
            sel_label = st.selectbox("Maç Seçin:", list(m_opt.keys()))
            sel_match = m_opt[sel_label]
            m_id = sel_match["id"]

            # Katılan Oyuncuları Getir
            m_players = supabase.table("match_players").select("user_id, custom_name, profiles(full_name)").eq("match_id", m_id).execute()
            player_uids = [p["user_id"] for p in m_players.data if p.get("user_id")]
            player_names = [get_player_display_name(p) for p in m_players.data]

            # MAÇA KATIL / AYRIL BUTONU (Grup Üyeleri İçin)
            if not is_left:
                col_join, col_info = st.columns([1, 3])
                with col_join:
                    if user_id in player_uids:
                        if st.button("❌ Maçtan Çık", key=f"leave_m_{m_id}"):
                            supabase.table("match_players").delete().eq("match_id", m_id).eq("user_id", user_id).execute()
                            st.rerun()
                    else:
                        if st.button("✅ Maça Katıl", key=f"join_m_{m_id}"):
                            supabase.table("match_players").insert({"match_id": m_id, "user_id": user_id}).execute()
                            st.rerun()

            # ADMIN ÖZEL: LİSTEDEN OYUNCU EKLE/ÇIKAR
            if group["is_admin"] and not is_left:
                with st.expander("👑 Admin: Oyuncu Kadrosunu Yönet"):
                    # Gruptaki tüm üyeler
                    grp_m = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).eq("is_left", False).execute()
                    m_dict = {get_profile_name(m.get("profiles")): m["user_id"] for m in grp_m.data}
                    
                    adm_selected = st.multiselect("Maç Kadrosundaki Üyeler:", options=list(m_dict.keys()), default=[k for k, v in m_dict.items() if v in player_uids])
                    
                    if st.button("Kadro Listesini Güncelle"):
                        # Mevcut üyeleri sil ve yenileri ekle
                        supabase.table("match_players").delete().eq("match_id", m_id).neq("user_id", None).execute()
                        to_add = [{"match_id": m_id, "user_id": m_dict[name]} for name in adm_selected]
                        if to_add:
                            supabase.table("match_players").insert(to_add).execute()
                        st.success("Kadro güncellendi!")
                        st.rerun()

            st.write("---")
            # KADRO VE SAHA GÖRÜNÜMÜ
            approved_draft = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("is_approved", True).execute()
            if approved_draft.data:
                st.success("🏆 **RESMİ MAÇ KADROSU ONAYLANDI**")
                render_pitch(approved_draft.data[0]["team_a"], approved_draft.data[0]["team_b"])
            else:
                st.info("Kadro henüz resmileşmedi. Oyuncu listesi aşağıda gösterilmektedir.")
                st.write("**Mevcut Oyuncular:**", ", ".join(player_names) if player_names else "Henüz kimse katılmadı.")

            # Gelecek Maç Sohbeti
            render_match_chat(m_id, user_id, is_left)
        else:
            st.info("Planlanmış maç bulunmuyor.")

    # TAB 2: MAÇ PLANLA (Sadece Admin)
    idx = 1
    if not is_left and group["is_admin"]:
        with tabs[idx]:
            st.subheader("➕ Yeni Maç Planla")
            m_date = st.date_input("Tarih")
            m_loc = st.text_input("Saha Adı", value="Merkez Halı Saha")
            if st.button("Maç Oluştur", use_container_width=True):
                supabase.table("matches").insert({"group_id": group["id"], "match_date": str(m_date), "location": m_loc, "created_by": user_id}).execute()
                st.success("Maç oluşturuldu!")
                st.rerun()
        idx += 1

    # TAB 3: ÜYELER VE İSTEKLER
    with tabs[idx]:
        st.subheader("🔗 Davet Linki")
        st.code(f"https://halisaha-takip.streamlit.app/?group_id={group['id']}", language="text")
        st.divider()

        st.subheader("👥 Üyeler")
        members = supabase.table("group_members").select("is_admin, is_left, profiles(full_name)").eq("group_id", group["id"]).execute()
        for m in members.data:
            st.write(f"- **{get_profile_name(m.get('profiles'))}** ({'⭐ Admin' if m['is_admin'] else '🏃 Oyuncu'})")

        if group["is_admin"] and not is_left:
            st.divider()
            st.subheader("🔔 Bekleyen İstekler")
            reqs = supabase.table("group_join_requests").select("id, user_id, profiles(full_name)").eq("group_id", group["id"]).eq("status", "pending").execute()
            for r in reqs.data:
                u_name = get_profile_name(r.get("profiles"))
                col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
                col_r1.write(f"**{u_name}**")
                if col_r2.button("✅ Onayla", key=f"a_{r['id']}"):
                    supabase.table("group_members").insert({"group_id": group["id"], "user_id": r["user_id"]}).execute()
                    supabase.table("group_join_requests").update({"status": "approved"}).eq("id", r["id"]).execute()
                    st.rerun()
                if col_r3.button("❌ Reddet", key=f"r_{r['id']}"):
                    supabase.table("group_join_requests").update({"status": "rejected"}).eq("id", r["id"]).execute()
                    st.rerun()
    idx += 1

    # TAB 4: GEÇMİŞ MAÇLAR VE SOHBET
    with tabs[idx]:
        st.subheader("📜 Oynanmış Geçmiş Maçlar & Maç Sohbetleri")
        past = [m for m in matches_list if str(m["match_date"]) < today_str]
        if past:
            p_opt = {f"{m['match_date']} - {m['location']}": m["id"] for m in past}
            sel_past_label = st.selectbox("Geçmiş Maç Seçin:", list(p_opt.keys()))
            sel_past_id = p_opt[sel_past_label]

            # Geçmiş Maç Performansı
            p_players = supabase.table("match_players").select("custom_name, goals, assists, profiles(full_name)").eq("match_id", sel_past_id).execute()
            t_data = [{"Oyuncu": get_player_display_name(p), "Gol": p.get("goals", 0), "Asist": p.get("assists", 0)} for p in p_players.data]
            st.table(t_data)

            # SOHBET VE MEDYA BÖLÜMÜ
            render_match_chat(sel_past_id, user_id, is_left)
        else:
            st.info("Oynanmış geçmiş maç bulunmuyor.")
    idx += 1

    # TAB 5: LEADERBOARD
    with tabs[idx]:
        st.subheader("🏆 Grup Puan Sıralaması")
        past_ids = [m["id"] for m in matches_list if str(m["match_date"]) < today_str]
        if past_ids:
            stats = supabase.table("match_players").select("custom_name, goals, assists, profiles(full_name)").in_("match_id", past_ids).execute()
            lb = {}
            for r in stats.data:
                name = get_player_display_name(r)
                g, a = r.get("goals") or 0, r.get("assists") or 0
                if name not in lb: lb[name] = {"Maç": 0, "Gol": 0, "Asist": 0, "Toplam Skoru": 0}
                lb[name]["Maç"] += 1; lb[name]["Gol"] += g; lb[name]["Asist"] += a; lb[name]["Toplam Skoru"] += (g + a)
            st.table(sorted([{"Oyuncu": k, **v} for k, v in lb.items()], key=lambda x: x["Toplam Skoru"], reverse=True))

# ---------------------------------------------------------
# ROUTER
# ---------------------------------------------------------
def main():
    if st.session_state.user is None:
        auth_screen()
    elif st.session_state.pending_group_id is not None:
        render_invite_confirmation_screen()
    else:
        if st.session_state.selected_group is None:
            main_dashboard()
        else:
            group_detail()

if __name__ == "__main__":
    main()
