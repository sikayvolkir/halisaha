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
    .comment-card {
        background-color: #161b22;
        border-left: 3px solid #238636;
        padding: 10px 15px;
        margin-bottom: 10px;
        border-radius: 4px;
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
# YARDIMCI FONKSİYONLAR: BİLDİRİM VE SAĞ ÜST ÜST BİLGİ
# ---------------------------------------------------------
def create_notification(user_id, title, message):
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message
        }).execute()
    except Exception:
        pass

def create_notification_for_group(group_id, title, message, exclude_user_id=None, admin_only=False):
    try:
        query = supabase.table("group_members").select("user_id, is_admin").eq("group_id", group_id).eq("is_left", False)
        if admin_only:
            query = query.eq("is_admin", True)
        members = query.execute()
        
        if members.data:
            notifications = []
            for m in members.data:
                uid = m["user_id"]
                if exclude_user_id and uid == exclude_user_id:
                    continue
                notifications.append({
                    "user_id": uid,
                    "title": title,
                    "message": message
                })
            if notifications:
                supabase.table("notifications").insert(notifications).execute()
    except Exception:
        pass

# BİLDİRİM LİSTELEME EKRANI (GÜNCELLENDİ)
def render_top_bar():
    if not st.session_state.user:
        return

    col_space, col_refresh, col_notif = st.columns([6, 1, 1])
    
    with col_refresh:
        if st.button("🔄 Yenile", use_container_width=True):
            st.rerun()

    with col_notif:
        user_id = st.session_state.user.id
        notifs_res = supabase.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        notifs = notifs_res.data if notifs_res.data else []
        
        count_label = f"🔔 Bildirimler ({len(notifs)})" if notifs else "🔔 Bildirimler"
        
        with st.popover(count_label, use_container_width=True):
            st.markdown("### 🔔 Bildirimleriniz")
            
            if notifs:
                if st.button("🗑️ Tümünü Temizle", use_container_width=True, key="clear_all_notifs"):
                    supabase.table("notifications").delete().eq("user_id", user_id).execute()
                    st.rerun()
                st.divider()

                for n in notifs:
                    nc1, nc2 = st.columns([5, 1])
                    with nc1:
                        st.markdown(f"**{n['title']}**")
                        st.write(f"{n['message']}")
                        if n.get("created_at"):
                            time_str = n['created_at'][:16].replace("T", " ")
                            st.caption(f"🕒 {time_str}")
                    with nc2:
                        if st.button("❌", key=f"del_notif_{n['id']}"):
                            supabase.table("notifications").delete().eq("id", n["id"]).execute()
                            st.rerun()
                    st.divider()
            else:
                st.caption("Henüz yeni bir bildiriminiz yok.")

# ---------------------------------------------------------
# SOHBET VE MEDYA PAYLAŞIM BİLEŞENİ
# ---------------------------------------------------------
def render_match_chat(match_id, user_id, group_id, is_left):
    st.markdown("---")
    st.write("### 💬 Maç Sohbeti & Medya Paylaşımı")
    
    try:
        msg_res = (
            supabase.table("match_messages")
            .select("*, profiles:user_id(full_name)")
            .eq("match_id", match_id)
            .order("created_at", desc=False)
            .execute()
        )
        messages_data = msg_res.data if msg_res.data else []
    except Exception:
        try:
            msg_res = (
                supabase.table("match_messages")
                .select("*")
                .eq("match_id", match_id)
                .order("created_at", desc=False)
                .execute()
            )
            messages_data = msg_res.data if msg_res.data else []
        except Exception:
            messages_data = []
    
    chat_container = st.container()
    with chat_container:
        if messages_data:
            for msg in messages_data:
                author = get_profile_name(msg.get("profiles"))
                time_str = msg.get("created_at", "")[:16].replace("T", " ")
                
                st.markdown(f"""
                <div class="chat-bubble">
                    <span class="chat-user">{author}</span> <span class="chat-time">{time_str}</span><br/>
                    <div style="margin-top:5px;">{msg.get('message') or ''}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if msg.get("media_url"):
                    if msg.get("media_type") == "image":
                        st.image(msg["media_url"], use_column_width=True)
                    elif msg.get("media_type") == "video":
                        st.video(msg["media_url"])
        else:
            st.caption("Henüz mesaj yok. İlk mesajı sen yaz!")

    if not is_left:
        with st.form(key=f"chat_form_{match_id}", clear_on_submit=True):
            user_msg = st.text_input("Mesajınız:", placeholder="Sohbete bir şeyler yazın...", key=f"input_msg_{match_id}")
            uploaded_file = st.file_uploader("Fotoğraf / Video Ekle", type=["jpg", "jpeg", "png", "mp4", "mov"], key=f"uploader_{match_id}")
            submit_btn = st.form_submit_button("📤 Gönder")

            if submit_btn:
                if user_msg.strip() or uploaded_file:
                    media_url = None
                    media_type = None

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

                    supabase.table("match_messages").insert({
                        "match_id": match_id,
                        "user_id": user_id,
                        "message": user_msg.strip(),
                        "media_url": media_url,
                        "media_type": media_type
                    }).execute()
                    
                    user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                    u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                    create_notification_for_group(group_id, "💬 Yeni Yorum/Medya", f"{u_name} maç sohbetine bir içerik ekledi.", exclude_user_id=user_id)
                    
                    st.rerun()

# ---------------------------------------------------------
# GRUP DAVET ONAY EKRANI
# ---------------------------------------------------------
def render_invite_confirmation_screen():
    render_top_bar()
    group_id = st.session_state.pending_group_id
    user_id = st.session_state.user.id

    group_res = supabase.table("groups").select("id, name").eq("id", group_id).execute()
    
    if not group_res.data:
        st.error("❌ Davet edildiğiniz grup bulunamadı veya silinmiş.")
        if st.button("Ana Sayfaya Git", use_container_width=True):
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()
        return

    group_data = group_res.data[0]

    member_check = supabase.table("group_members").select("*").eq("group_id", group_id).eq("user_id", user_id).execute()
    if member_check.data:
        st.success(f"🎉 **{group_data['name']}** grubunun zaten bir üyesisiniz!")
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

    req_check = supabase.table("group_join_requests").select("*").eq("group_id", group_id).eq("user_id", user_id).eq("status", "pending").execute()
    if req_check.data:
        st.info(f"⏳ **{group_data['name']}** grubuna katılım isteğiniz zaten iletilmiş. Admin onayı bekleniyor.")
        if st.button("Ana Sayfaya Dön", use_container_width=True):
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()
        return

    st.markdown("<h2 class='main-title'>⚽ GRUP DAVETİ</h2>", unsafe_allow_html=True)
    st.info(f"**{group_data['name']}** grubuna katılmak üzere davet edildiniz.")
    st.write("Gruba katılma isteği gönderdikten sonra grup admini onayladığında maç kadrolarına dahil olabilirsiniz.")
    st.divider()

    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button("✅ İsteği Admin'e Gönder", use_container_width=True):
            try:
                supabase.table("group_join_requests").insert({
                    "group_id": group_id,
                    "user_id": user_id,
                    "status": "pending"
                }).execute()
                
                user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir kullanıcı"
                create_notification_for_group(group_id, "🙋‍♂️ Yeni Katılım İsteği", f"{u_name} gruba katılmak için istek gönderdi.", admin_only=True)

                st.success("🎉 Katılım isteğiniz grup adminine iletildi!")
                st.session_state.pending_group_id = None
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"İstek gönderilirken hata oluştu: {e}")

    with col_reject:
        if st.button("❌ Vazgeç / İptal Et", use_container_width=True):
            st.session_state.pending_group_id = None
            st.query_params.clear()
            st.rerun()

# ---------------------------------------------------------
# Kimlik Doğrulama Ekranı
# ---------------------------------------------------------
def auth_screen():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    
    if st.session_state.pending_group_id is not None:
        st.warning("👋 Bir gruba katılmak için davet edildiniz! Lütfen kendi hesabınızla giriş yapın veya yeni bir hesap oluşturun.")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        st.subheader("Giriş Yap")
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("E-Posta", key="login_email")
            password = st.text_input("Şifre", type="password", key="login_password")
            submit_login = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if submit_login:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.success("Giriş başarılı!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Giriş başarısız: {e}")

    with tab2:
        st.subheader("Yeni Hesap Oluştur")
        with st.form("register_form", clear_on_submit=False):
            full_name = st.text_input("Ad Soyad", key="reg_name")
            email = st.text_input("E-Posta", key="reg_email")
            password = st.text_input("Şifre (En az 6 karakter)", type="password", key="reg_password")
            submit_reg = st.form_submit_button("Kayıt Ol", use_container_width=True)
            
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kayıt işlemi başarısız: {e}")

# ---------------------------------------------------------
# Ana Dashboard
# ---------------------------------------------------------
def main_dashboard():
    render_top_bar()
    st.markdown("<h1 class='main-title'>⚽ HALISAHA GRUPLARIM</h1>", unsafe_allow_html=True)
    user_id = st.session_state.user.id
    
    if st.button("🚪 Oturumu Kapat"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.selected_group = None
        st.session_state.pending_group_id = None
        st.query_params.clear()
        st.rerun()

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Dahil Olduğunuz Gruplar")
        memberships = supabase.table("group_members").select("group_id, is_admin, is_left, groups(id, name)").eq("user_id", user_id).execute()
        
        my_group_ids = []
        if memberships.data:
            for item in memberships.data:
                group = item.get("groups")
                if not group:
                    continue
                
                my_group_ids.append(group["id"])
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
                                st.success("Gruptan çıkıldı.")
                                st.rerun()
                        if is_admin:
                            if st.button("🗑️ Grubu Sil", key=f"del_{group['id']}"):
                                supabase.table("groups").delete().eq("id", group["id"]).execute()
                                st.success("Grup silindi.")
                                st.rerun()
                st.divider()
        else:
            st.info("Henüz herhangi bir gruba dahil değilsiniz.")

        st.subheader("🔍 Grup Ara & Katıl")
        search_query = st.text_input("Grup Adı Ara", placeholder="Aramak istediğiniz grubun adını yazın...", key="search_group_input")
        
        if search_query.strip():
            search_res = supabase.table("groups").select("id, name").ilike("name", f"%{search_query.strip()}%").execute()
            
            if search_res.data:
                user_requests = supabase.table("group_join_requests").select("group_id, status").eq("user_id", user_id).execute()
                pending_group_ids = [r["group_id"] for r in user_requests.data if r.get("status") == "pending"]

                found_any = False
                for g in search_res.data:
                    if g["id"] in my_group_ids:
                        continue
                    
                    found_any = True
                    g_col1, g_col2 = st.columns([3, 1])
                    g_col1.write(f"⚽ **{g['name']}**")
                    
                    if g["id"] in pending_group_ids:
                        g_col2.button("⏳ İstek Beklemede", key=f"req_pend_{g['id']}", disabled=True)
                    else:
                        if g_col2.button("➕ İstek Gönder", key=f"req_send_{g['id']}"):
                            try:
                                supabase.table("group_join_requests").insert({
                                    "group_id": g["id"],
                                    "user_id": user_id,
                                    "status": "pending"
                                }).execute()
                                
                                user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                                u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir kullanıcı"
                                create_notification_for_group(g["id"], "🙋‍♂️ Yeni Katılım İsteği", f"{u_name} gruba katılmak için istek gönderdi.", admin_only=True)

                                st.success(f"'{g['name']}' grubuna katılım isteğiniz gönderildi!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"İstek gönderilemedi: {e}")
                if not found_any:
                    st.caption("Aramanıza uygun katılabileceğiniz yeni bir grup bulunamadı.")
            else:
                st.caption("Eşleşen grup bulunamadı.")

    with col2:
        st.subheader("Yeni Grup Oluştur")
        with st.form("create_group_form", clear_on_submit=True):
            new_group_name = st.text_input("Grup Adı")
            submit_group = st.form_submit_button("Grubu Kur", use_container_width=True)
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
                        st.error(f"Hata: {e}")
                else:
                    st.warning("Lütfen grup adı girin.")

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
    render_top_bar()
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    is_left = group.get("is_left", False)
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)

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
            selected_match_label = st.selectbox("Maç Seçin:", list(match_options.keys()), key="upcoming_select")
            selected_match = match_options[selected_match_label]
            m_id = selected_match["id"]

            players_res = supabase.table("match_players").select("user_id, custom_name, profiles(full_name)").eq("match_id", m_id).execute()
            player_uids = [p["user_id"] for p in players_res.data if p.get("user_id")]
            player_names = [get_player_display_name(p) for p in players_res.data]
            if not player_names:
                player_names = ["Oyuncu Bulunamadı"]

            # MAÇA KATIL / AYRIL BUTONU BÖLÜMÜ
            if not is_left:
                st.markdown("#### 🏃‍♂️ Maç Katılım Durumunuz")
                col_join_btn, col_join_info = st.columns([1, 3])
                with col_join_btn:
                    if user_id in player_uids:
                        if st.button("❌ Maçtan Çık", key=f"btn_leave_m_{m_id}", use_container_width=True):
                            # 1. Oyuncu adını al
                            current_user_name = None
                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            if user_prof.data and user_prof.data[0].get("full_name"):
                                current_user_name = user_prof.data[0]["full_name"]

                            # 2. Veritabanından (match_players) Oyuncuyu Sil
                            supabase.table("match_players").delete().eq("match_id", m_id).eq("user_id", user_id).execute()
                            
                            # 3. Veritabanındaki TÜM kadro taslaklarından (match_squad_drafts) bu kişiyi temizle
                            if current_user_name:
                                all_drafts = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).execute()
                                if all_drafts.data:
                                    for d in all_drafts.data:
                                        t_a = [p for p in d.get("team_a", []) if p != current_user_name]
                                        t_b = [p for p in d.get("team_b", []) if p != current_user_name]
                                        supabase.table("match_squad_drafts").update({
                                            "team_a": t_a,
                                            "team_b": t_b
                                        }).eq("id", d["id"]).execute()

                            # 4. Eğer Onaylanmış Resmi Kadro Varsa İptal Et ve Admine Bildirim Gönder
                            approved_draft = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("is_approved", True).execute()
                            was_approved = len(approved_draft.data) > 0

                            if was_approved:
                                supabase.table("match_squad_drafts").update({"is_approved": False}).eq("match_id", m_id).execute()

                            # 5. Session State Üzerindeki Geçici Kadro Seçimlerinden Temizle
                            if current_user_name:
                                if "current_team_a" in st.session_state and current_user_name in st.session_state.current_team_a:
                                    st.session_state.current_team_a.remove(current_user_name)
                                if "current_team_b" in st.session_state and current_user_name in st.session_state.current_team_b:
                                    st.session_state.current_team_b.remove(current_user_name)

                            # 6. Bildirim Gönderimi
                            u_name = current_user_name if current_user_name else "Bir üye"
                            create_notification_for_group(group["id"], "🏃‍♂️ Maç Katılımı", f"{u_name} maç kadrosundan ayrıldı.", exclude_user_id=user_id)
                            
                            if was_approved:
                                create_notification_for_group(group["id"], "⚠️ Onaylı Kadro Bozuldu", f"{u_name} maçtan ayrıldığı için onaylanmış kadro iptal edildi. Tekrar onaylamanız gerekiyor.", admin_only=True)

                            st.rerun()
                    else:
                        if st.button("✅ Maça Katıl", key=f"btn_join_m_{m_id}", use_container_width=True):
                            supabase.table("match_players").insert({"match_id": m_id, "user_id": user_id}).execute()
                            
                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                            create_notification_for_group(group["id"], "🏃‍♂️ Maç Katılımı", f"{u_name} maça katıldı!", exclude_user_id=user_id)
                            
                            st.rerun()

            st.write("---")

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
                                    
                                    create_notification_for_group(group["id"], "📢 Resmi Kadro İlan Edildi", f"{selected_match['match_date']} tarihli maçın kadrosu resmi olarak ilan edildi!")
                                    
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
                            if p1 != p2:
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
                            if p1 != p2:
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
                                swap_candidate = [x for x in t_a if x != p1][0] if len(t_a) > 1 else None
                                if swap_candidate:
                                    t_a.remove(swap_candidate); t_b.append(swap_candidate)
                                    t_b.remove(p2); t_a.append(p2)
                            elif p1 in t_b and p2 in t_a:
                                swap_candidate = [x for x in t_b if x != p1][0] if len(t_b) > 1 else None
                                if swap_candidate:
                                    t_b.remove(swap_candidate); t_a.append(swap_candidate)
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

                    st.markdown("#### 🏟️ Canlı Kadro Görünümü")
                    render_pitch(selected_a, selected_b)

                    st.write("---")
                    save_col, send_col = st.columns(2)
                    
                    with save_col:
                        if st.button("💾 Taslağı Kaydet", use_container_width=True):
                            data = {
                                "match_id": m_id,
                                "user_id": user_id,
                                "team_a": selected_a,
                                "team_b": selected_b,
                                "together_pairs": together_pairs,
                                "separate_pairs": separate_pairs
                            }
                            supabase.table("match_squad_drafts").upsert(data, on_conflict="match_id, user_id").execute()
                            st.success("Taslağınız kaydedildi!")
                    
                    with send_col:
                        btn_label = "📢 İlan Et & Resmi Kadro Yap" if group["is_admin"] else "📨 Admine Kadro Önerisini Gönder"
                        if st.button(btn_label, use_container_width=True):
                            is_appr = True if group["is_admin"] else False
                            data = {
                                "match_id": m_id,
                                "user_id": user_id,
                                "team_a": selected_a,
                                "team_b": selected_b,
                                "together_pairs": together_pairs,
                                "separate_pairs": separate_pairs,
                                "is_approved": is_appr
                            }
                            supabase.table("match_squad_drafts").upsert(data, on_conflict="match_id, user_id").execute()
                            
                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                            
                            if group["is_admin"]:
                                create_notification_for_group(group["id"], "📢 Resmi Kadro İlan Edildi", f"{selected_match['match_date']} tarihli maçın kadrosu onaylandı!")
                            else:
                                create_notification_for_group(group["id"], "📋 Kadro Önerisi", f"{u_name} yeni bir kadro önerisi gönderdi.", admin_only=True)

                            st.success("İşlem başarılı!")
                            st.rerun()

            # GELECEK MAÇ SOHBET BÖLÜMÜ
            render_match_chat(m_id, user_id, group["id"], is_left)
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
                            
                            create_notification_for_group(group["id"], "⚽ Yeni Maç Açıldı!", f"{match_date} tarihli yeni bir maç planlandı.")

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
                    custom_name_val = st.text_input("Dışarıdan Gelecek Oyuncunun Adı Soyadı:")
                    submit_custom_p = st.form_submit_button("➕ Oyuncuyu Kadroya Dahil Et")
                    
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

    # =========================================================
    # TAB: GRUP ÜYELERİ & SADECE GRUP PAYLAŞIM LİNKİ
    # =========================================================
    with tab_members:
        st.subheader("🔗 Gruba Davet Linki")
        base_url = "https://halisaha-takip.streamlit.app"
        invite_link = f"{base_url}/?group_id={group['id']}"
        st.code(invite_link, language="text")
        st.caption("Bu linki paylaştığınızda; kullanıcı oturum açmışsa onay ekranı gelir, oturumu yoksa giriş yaptıktan sonra onay ekranı açılır.")
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
                        
                        create_notification(req["user_id"], "🎉 Grub Katılımı Onaylandı!", f"'{group['name']}' grubuna katılım isteğiniz onaylandı.")

                        st.success(f"{u_name} gruba eklendi!")
                        st.rerun()
                        
                    if col_req_3.button("❌ Reddet", key=f"rej_{req['id']}"):
                        supabase.table("group_join_requests").update({"status": "rejected"}).eq("id", req["id"]).execute()
                        st.info(f"{u_name} isteği reddedildi.")
                        st.rerun()

    # =========================================================
    # TAB: GEÇMİŞ MAÇLAR
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

            # GEÇMİŞ MAÇ SOHBET VE MEDYA BÖLÜMÜ
            render_match_chat(selected_match_id, user_id, group["id"], is_left)
        else:
            st.info("Henüz oynanmış geçmiş bir maç bulunmuyor.")

    # =========================================================
    # TAB: PUAN SIRALAMASI
    # =========================================================
    with tab_leaderboard:
        st.subheader("🏆 Grup Puan ve Performans Sıralaması")
        past_match_ids = [m["id"] for m in matches_list if str(m["match_date"]) < today_str]
        
        if past_match_ids:
            stats_res = supabase.table("match_players").select("user_id, custom_name, goals, assists, profiles(full_name)").in_("match_id", past_match_ids).execute()
            if stats_res.data:
                leaderboard = {}
                for row in stats_res.data:
                    name = get_player_display_name(row)
                    goals = row.get("goals") or 0
                    assists = row.get("assists") or 0
                    
                    if name not in leaderboard:
                        leaderboard[name] = {"Maç Sayısı": 0, "Toplam Gol": 0, "Toplam Asist": 0, "Toplam Skoru (Skor Katkısı)": 0}
                    
                    leaderboard[name]["Maç Sayısı"] += 1
                    leaderboard[name]["Toplam Gol"] += goals
                    leaderboard[name]["Toplam Asist"] += assists
                    leaderboard[name]["Toplam Skoru (Skor Katkısı)"] += (goals + assists)

                lb_list = [{"Oyuncu": k, **v} for k, v in leaderboard.items()]
                lb_list = sorted(lb_list, key=lambda x: x["Toplam Skoru (Skor Katkısı)"], reverse=True)
                
                st.table(lb_list)
            else:
                st.info("İstatistik bulunamadı.")
        else:
            st.info("Henüz istatistiki veri oluşturacak geçmiş bir maç oynanmadı.")

# ---------------------------------------------------------
# UYGULAMA YÖNLENDİRME MERKEZİ (ROUTING)
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
