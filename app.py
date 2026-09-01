import streamlit as st
from supabase import create_client, Client
import random
from datetime import date
import uuid

st.set_page_config(page_title="Halısaha Takip", page_icon="⚽", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #f0f6fc; }
    .main-title { color: #2ea44f; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .stButton > button { background-color: #238636; color: white; border-radius: 6px; border: none; padding: 8px 16px; font-weight: bold; }
    .stButton > button:hover { background-color: #2ea44f; color: white; }
    .chat-bubble { background-color: #161b22; border-left: 4px solid #238636; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; }
    .chat-user { font-weight: bold; color: #58a6ff; font-size: 0.9rem; }
    .chat-time { color: #8b949e; font-size: 0.75rem; float: right; }
    .pitch-container { background-color: #2e7d32; background-image: linear-gradient(to right, rgba(255,255,255,0.15) 50%, transparent 50%); background-size: 80px 100%; border: 4px solid #ffffff; border-radius: 12px; padding: 20px; margin: 15px 0; position: relative; min-height: 350px; display: flex; justify-content: space-between; }
    .pitch-half { width: 48%; z-index: 2; }
    .pitch-center-line { position: absolute; left: 50%; top: 0; bottom: 0; width: 3px; background-color: rgba(255, 255, 255, 0.7); z-index: 1; }
    .pitch-team-title-a, .pitch-team-title-b { color: #ffffff; font-weight: bold; font-size: 1.2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); margin-bottom: 15px; }
    .player-chip-container { display: flex; flex-wrap: wrap; gap: 8px; }
    .player-chip { background-color: #1f6feb; color: white; padding: 8px 14px; border-radius: 20px; font-size: 0.95rem; font-weight: 600; box-shadow: 0 4px 8px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.5); }
    .player-chip-b { background-color: #da3633; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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

def create_notification(user_id, title, message):
    try:
        supabase.table("notifications").insert({
            "user_id": user_id,
            "title": title,
            "message": message
        }).execute()
    except Exception as e:
        st.error(f"Bildirim hatası: {e}")

def create_notification_for_group(group_id, title, message, exclude_user_id=None, admin_only=False):
    try:
        query = supabase.table("group_members").select("user_id, is_admin").eq("group_id", group_id).neq("is_left", True)
        if admin_only:
            query = query.eq("is_admin", True)
        members = query.execute()
        
        if members.data:
            for m in members.data:
                uid = m["user_id"]
                if exclude_user_id and str(uid) == str(exclude_user_id):
                    continue
                create_notification(uid, title, message)
    except Exception as e:
        print(f"Grup bildirimi hatası: {e}")

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

def render_match_chat(match_id, user_id, group_id, is_left):
    st.markdown("---")
    st.write("### 💬 Maç Sohbeti & Medya Paylaşımı")
    
    try:
        msg_res = (
            supabase.table("match_messages")
            .select("*, profiles!match_messages_user_id_fkey(full_name)")
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

    uids = list(set([m["user_id"] for m in messages_data if m.get("user_id")]))
    profiles_map = {}
    if uids:
        p_res = supabase.table("profiles").select("id, full_name").in_("id", uids).execute()
        if p_res.data:
            profiles_map = {p["id"]: p.get("full_name") for p in p_res.data}
    
    chat_container = st.container()
    with chat_container:
        if messages_data:
            for msg in messages_data:
                msg_uid = msg.get("user_id")
                author = profiles_map.get(msg_uid) or get_profile_name(msg.get("profiles"))
                time_str = msg.get("created_at", "")[:16].replace("T", " ")
                is_my_message = (msg_uid == user_id)
                
                if is_my_message:
                    nc1, nc2 = st.columns([5, 1])
                    with nc1:
                        st.markdown(f"""
                        <div class="chat-bubble">
                            <span class="chat-user">{author}</span> <span class="chat-time">{time_str}</span><br/>
                            <div style="margin-top:5px;">{msg.get('message') or ''}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        if msg.get("media_url"):
                            if msg.get("media_type") == "image":
                                st.image(msg["media_url"], use_container_width=True)
                            elif msg.get("media_type") == "video":
                                st.video(msg["media_url"])
                    with nc2:
                        if st.button("❌", key=f"del_msg_{msg['id']}"):
                            supabase.table("match_messages").delete().eq("id", msg["id"]).execute()
                            st.rerun()
                else:
                    st.markdown(f"""
                    <div class="chat-bubble">
                        <span class="chat-user">{author}</span> <span class="chat-time">{time_str}</span><br/>
                        <div style="margin-top:5px;">{msg.get('message') or ''}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if msg.get("media_url"):
                        if msg.get("media_type") == "image":
                            st.image(msg["media_url"], use_container_width=True)
                        elif msg.get("media_type") == "video":
                            st.video(msg["media_url"])
        else:
            st.caption("Henüz mesaj yok. İlk mesajı sen yaz!")

    if not is_left:
        with st.form(key=f"chat_form_{match_id}", clear_on_submit=True):
            user_msg = st.text_input("Mesajınız:", placeholder="Sohbete bir şey yazın...", key=f"input_msg_{match_id}")
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

                    current_active_user_id = st.session_state.user.id

                    supabase.table("match_messages").insert({
                        "match_id": match_id,
                        "user_id": current_active_user_id,
                        "message": user_msg.strip(),
                        "media_url": media_url,
                        "media_type": media_type
                    }).execute()
                    
                    user_prof = supabase.table("profiles").select("full_name").eq("id", current_active_user_id).execute()
                    u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                    create_notification_for_group(group_id, "💬 Yeni Yorum/Medya", f"{u_name} maç sohbetine bir içerik ekledi.", exclude_user_id=current_active_user_id)
                    
                    st.rerun()

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
                        if res.user:
                            supabase.table("profiles").upsert({"id": res.user.id, "full_name": full_name}).execute()
                            st.session_state.user = res.user
                            st.success("Kayıt başarılı!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Kayıt işlemi başarısız: {e}")

def main_dashboard():
    render_top_bar()
    st.markdown("<h1 class='main-title'>⚽ HALISAHA GRUPLARIM</h1>", unsafe_allow_html=True)
    user_id = st.session_state.user.id
    
    if st.button("🚪 Oturumu Kapat"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
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

def group_detail():
    render_top_bar()
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    is_left = group.get("is_left", False)
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)

    # Sekmeler kullanıcı rolüne göre dinamik ve sadece admine görünecek şekilde ayarlandı
    tabs_list = ["📅 Gelecek Maçlar & Kadrolar"]
    if not is_left and group["is_admin"]:
        tabs_list.append("➕ Maç Planla")
        tabs_list.append("➕ Dışarıdan Oyuncu Ekle (Admin)")
            
    tabs_list.extend(["👥 Grup Üyeleri & İstekler", "📜 Geçmiş Maçlar", "🏆 Puan Sıralaması"])

    tabs = st.tabs(tabs_list)
    
    tab_upcoming = tabs[0]
    
    idx = 1
    tab_create = None
    tab_custom_player = None
    
    if not is_left and group["is_admin"]:
        tab_create = tabs[idx]
        idx += 1
        tab_custom_player = tabs[idx]
        idx += 1

    tab_members = tabs[idx]
    tab_past = tabs[idx+1]
    tab_leaderboard = tabs[idx+2]
    
    today_str = str(date.today())
    all_matches = supabase.table("matches").select("*").eq("group_id", group["id"]).execute()
    matches_list = all_matches.data if all_matches.data else []

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
                player_names = ["Henüz Katılımcı Yok"]

            if not is_left:
                st.markdown("#### 🏃‍♂️ Maç Katılım Durumunuz")
                col_join_btn, col_join_info = st.columns([1, 3])
                with col_join_btn:
                    if user_id in player_uids:
                        if st.button("❌ Maçtan Çık", key=f"btn_leave_m_{m_id}", use_container_width=True):
                            current_user_name = None
                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            if user_prof.data and user_prof.data[0].get("full_name"):
                                current_user_name = user_prof.data[0]["full_name"]

                            supabase.table("match_players").delete().eq("match_id", m_id).eq("user_id", user_id).execute()
                            
                            if "current_team_a" in st.session_state: del st.session_state["current_team_a"]
                            if "current_team_b" in st.session_state: del st.session_state["current_team_b"]

                            u_name = current_user_name if current_user_name else "Bir üye"
                            create_notification_for_group(group["id"], "🏃‍♂️ Maç Katılımı", f"{u_name} maç kadrosundan ayrıldı.", exclude_user_id=user_id)
                            st.rerun()
                    else:
                        if st.button("✅ Maça Katıl", key=f"btn_join_m_{m_id}", use_container_width=True):
                            supabase.table("match_players").insert({"match_id": m_id, "user_id": user_id}).execute()
                            
                            if "current_team_a" in st.session_state: del st.session_state["current_team_a"]
                            if "current_team_b" in st.session_state: del st.session_state["current_team_b"]

                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                            create_notification_for_group(group["id"], "🏃‍♂️ Maç Katılımı", f"{u_name} maça katıldı!", exclude_user_id=user_id)
                            
                            st.rerun()

            st.write("---")

            approved_draft = supabase.table("match_squad_drafts").select("*").eq("match_id", m_id).eq("is_approved", True).execute()
            
            if approved_draft.data:
                st.success("🏆 **BU MAÇIN RESMİ KADROSU İLAN EDİLDİ!**")
                official = approved_draft.data[0]
                render_pitch(official["team_a"], official["team_b"])
                
                if group["is_admin"] and not is_left:
                    if st.button("🔄 Kadro Onayını Kaldır ve Yeniden Düzenle", key=f"unapprove_{official['id']}"):
                        supabase.table("match_squad_drafts").update({"is_approved": False}).eq("id", official["id"]).execute()
                        st.rerun()
            else:
                st.info("💡 Resmi kadro henüz ilan edilmedi. Aşağıdan kadro önerisi yapabilir veya kendi taslağınızı oluşturabilirsiniz.")
                
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

                if not is_left and player_names != ["Henüz Katılımcı Yok"]:
                    st.markdown("### 🛠️ Kendi Kadro Taslağını Kur")
                    
                    st.markdown("#### 1️⃣ Oyuncu İlişki Şartları")
                    col_to, col_sep = st.columns(2)
                    
                    together_pairs = []
                    with col_to:
                        st.caption("🤝 Beraber Oynaması İstenen İkililer")
                        for i in range(st.session_state.together_count):
                            c1, c2 = st.columns(2)
                            p1 = c1.selectbox(f"Birlikte #{i+1} Oyuncu A", player_names, key=f"tog_a_{i}_{m_id}")
                            p2 = c2.selectbox(f"Birlikte #{i+1} Oyuncu B", player_names, key=f"tog_b_{i}_{m_id}")
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
                            p1 = c1.selectbox(f"Ayrı #{i+1} Oyuncu A", player_names, key=f"sep_a_{i}_{m_id}")
                            p2 = c2.selectbox(f"Ayrı #{i+1} Oyuncu B", player_names, key=f"sep_b_{i}_{m_id}")
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
                            key=f"man_select_a_{m_id}"
                        )
                    
                    remaining_for_b = [p for p in player_names if p not in selected_a]
                    
                    with man_col_b:
                        selected_b = st.multiselect(
                            "🔴 B Takımı Oyuncuları", 
                            options=remaining_for_b, 
                            default=[p for p in st.session_state.current_team_b if p in remaining_for_b],
                            key=f"man_select_b_{m_id}"
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
                            existing_draft = supabase.table("match_squad_drafts").select("id").eq("match_id", m_id).eq("user_id", user_id).execute()
                            if existing_draft.data:
                                supabase.table("match_squad_drafts").update(data).eq("id", existing_draft.data[0]["id"]).execute()
                            else:
                                supabase.table("match_squad_drafts").insert(data).execute()
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
                            existing_draft = supabase.table("match_squad_drafts").select("id").eq("match_id", m_id).eq("user_id", user_id).execute()
                            if existing_draft.data:
                                supabase.table("match_squad_drafts").update(data).eq("id", existing_draft.data[0]["id"]).execute()
                            else:
                                supabase.table("match_squad_drafts").insert(data).execute()
                            
                            user_prof = supabase.table("profiles").select("full_name").eq("id", user_id).execute()
                            u_name = get_profile_name(user_prof.data[0]) if user_prof.data else "Bir üye"
                            
                            if group["is_admin"]:
                                create_notification_for_group(group["id"], "📢 Resmi Kadro İlan Edildi", f"{selected_match['match_date']} tarihli maçın kadrosu onaylandı!")
                            else:
                                create_notification_for_group(group["id"], "📋 Kadro Önerisi", f"{u_name} yeni bir kadro önerisi gönderdi.", admin_only=True)

                            st.success("İşlem başarılı!")
                            st.rerun()

            # Sadece admindeyse seçili maçı en alttan sikebilme özelliği
            if group["is_admin"]:
                st.markdown("---")
                if st.button("🗑️ Maçı Sil", key=f"del_upcoming_match_{m_id}", use_container_width=True):
                    try:
                        supabase.table("matches").delete().eq("id", m_id).execute()
                        st.success("Maç silindi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Maç silinirken hata oluştu: {e}")

            render_match_chat(m_id, user_id, group["id"], is_left)
        else:
            st.info("Planlanmış gelecek bir maç bulunmuyor.")

    if tab_create:
        with tab_create:
            if group["is_admin"]:
                st.subheader("➕ Yeni Maç Planla")
                match_date = st.date_input("Maç Tarihi")
                location = st.text_input("Halı Saha / Saha Adı", value="Merkez Halı Saha")
                
                members_data = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).neq("is_left", True).execute()
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

    with tab_members:
        st.subheader("🔗 Gruba Davet Linki")
        base_url = "https://halisaha-takip.streamlit.app"
        invite_link = f"{base_url}/?group_id={group['id']}"
        st.code(invite_link, language="text")
        st.caption("Bu linki paylaştığınızda; kullanıcı oturum açmışsa onay ekranı gelir, oturumu yoksa giriş yaptıktan sonra onay ekranı açılır.")
        st.divider()

        st.subheader("👥 Grup Üyeleri")
        members = supabase.table("group_members").select("user_id, is_admin, is_left, profiles(full_name)").eq("group_id", group["id"]).execute()
        
        for m in members.data:
            name = get_profile_name(m.get("profiles"))
            status = " (Ayrıldı)" if m.get("is_left") else ""
            role = "⭐ Admin" if m["is_admin"] else "🏃 Oyuncu"
            
            col_m1, col_m2 = st.columns([5, 1])
            with col_m1:
                st.write(f"- **{name}** ({role}){status}")
            
            # Admin için her üyenin yanında üç nokta menüsü (gruptan çıkarma ve adminlik verme)
            if group["is_admin"] and not is_left and str(m["user_id"]) != str(user_id):
                with col_m2:
                    with st.popover("⋮"):
                        if not m["is_admin"]:
                            if st.button("⭐ Admin Yap", key=f"make_admin_{m['user_id']}"):
                                supabase.table("group_members").update({"is_admin": True}).eq("group_id", group["id"]).eq("user_id", m["user_id"]).execute()
                                create_notification(m["user_id"], "⭐ Admin Yetkisi", f"'{group['name']}' grubunda admin yapıldınız.")
                                st.success(f"{name} admin yapıldı!")
                                st.rerun()
                        
                        if st.button("❌ Gruptan Çıkar", key=f"kick_user_{m['user_id']}"):
                            supabase.table("group_members").delete().eq("group_id", group["id"]).eq("user_id", m["user_id"]).execute()
                            create_notification(m["user_id"], "🚪 Gruptan Çıkarıldınız", f"'{group['name']}' grubundan çıkarıldınız.")
                            st.success(f"{name} gruptan çıkarıldı!")
                            st.rerun()
            
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
                        
                        create_notification(req["user_id"], "🎉 Grup Katılımı Onaylandı!", f"'{group['name']}' grubuna katılım isteğiniz onaylandı.")

                        st.success(f"{u_name} gruba eklendi!")
                        st.rerun()
                        
                    if col_req_3.button("❌ Reddet", key=f"rej_{req['id']}"):
                        supabase.table("group_join_requests").update({"status": "rejected"}).eq("id", req["id"]).execute()
                        st.info(f"{u_name} isteği reddedildi.")
                        st.rerun()

    with tab_past:
        st.subheader("📜 Oynanmış Geçmiş Maçlar")
        past_matches_data = [m for m in matches_list if str(m["match_date"]) < today_str]
        
        if past_matches_data:
            match_options = {f"{m['match_date']} - {m['location']}": m["id"] for m in past_matches_data}
            selected_match_label = st.selectbox("Bir Geçmiş Maç Seçin:", list(match_options.keys()))
            selected_match_id = match_options[selected_match_label]
            
            players_res = supabase.table("match_players").select("id, user_id, custom_name, goals, assists, profiles(full_name)").eq("match_id", selected_match_id).execute()
            players_in_match = players_res.data if players_res.data else []

            st.write("#### 📊 Maç Kadrosu & İstatistik Güncelleme")
            st.caption("Her kullanıcı kendi istatistiklerini (veya admin herkesinkini) güncelleyebilir.")

            for p in players_in_match:
                p_name = get_player_display_name(p)
                p_uid = p.get("user_id")
                
                can_edit = group["is_admin"] or (p_uid and str(p_uid) == str(user_id))
                
                with st.container():
                    col_p1, col_p2, col_p3, col_p4 = st.columns([3, 1, 1, 1])
                    col_p1.write(f"👤 **{p_name}** {'(Sen)' if p_uid and str(p_uid) == str(user_id) else ''}")
                    col_p2.write(f"⚽ Gol: **{p.get('goals', 0)}**")
                    col_p3.write(f"👟 Asist: **{p.get('assists', 0)}**")
                    
                    if can_edit and not is_left:
                        with col_p4:
                            with st.popover("✏️ Düzenle"):
                                with st.form(key=f"form_stat_{p['id']}"):
                                    new_goals = st.number_input("Gol", min_value=0, value=p.get("goals", 0), key=f"g_{p['id']}")
                                    new_assists = st.number_input("Asist", min_value=0, value=p.get("assists", 0), key=f"a_{p['id']}")
                                    if st.form_submit_button("Kaydet"):
                                        supabase.table("match_players").update({"goals": new_goals, "assists": new_assists}).eq("id", p["id"]).execute()
                                        st.success("Güncellendi!")
                                        st.rerun()
                    st.divider()

            st.write("#### ⭐ Maçın Adamı (Man of the Match) Oylaması")
            votes_res = supabase.table("match_motm_votes").select("*").eq("match_id", selected_match_id).execute()
            all_votes = votes_res.data if votes_res.data else []
            
            my_vote = next((v for v in all_votes if v.get("user_id") == user_id), None)
            
            vote_options = {get_player_display_name(p): p for p in players_in_match}
            
            if not is_left:
                with st.form(key=f"motm_form_{selected_match_id}"):
                    current_voted_player_name = None
                    if my_vote:
                        voted_p_obj = next((p for p in players_in_match if p.get("id") == my_vote.get("voted_player_id") or (p.get("user_id") and str(p.get("user_id")) == str(my_vote.get("voted_player_id")))), None)
                        if voted_p_obj:
                            current_voted_player_name = get_player_display_name(voted_p_obj)
                        elif my_vote.get("voted_player_name"):
                            current_voted_player_name = my_vote.get("voted_player_name")
                    
                    default_idx = 0
                    opt_keys = list(vote_options.keys())
                    if current_voted_player_name in opt_keys:
                        default_idx = opt_keys.index(current_voted_player_name)
                        
                    sel_voted_name = st.selectbox("Bu maçın adamı kimdi?", opt_keys, index=default_idx)
                    submit_vote = st.form_submit_button("🗳️ Oyumu Kaydet / Değiştir")
                    
                    if submit_vote and sel_voted_name:
                        target_p = vote_options[sel_voted_name]
                        target_id = target_p.get("user_id") if target_p.get("user_id") else target_p.get("id")
                        
                        vote_data = {
                            "match_id": selected_match_id,
                            "user_id": user_id,
                            "voted_player_id": str(target_id),
                            "voted_player_name": sel_voted_name
                        }
                        
                        try:
                            supabase.table("match_motm_votes").upsert(
                                vote_data, 
                                on_conflict="match_id,user_id"
                            ).execute()
                            
                            st.success("Oyunuz başarıyla kaydedildi!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Oy kaydedilirken hata oluştu: {e}")

            vote_counts = {}
            for v in all_votes:
                p_name = v.get("voted_player_name")
                if p_name:
                    vote_counts[p_name] = vote_counts.get(p_name, 0) + 1
            
            if vote_counts:
                st.caption("📊 Anlık Oy Dağılımı:")
                for pn, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- **{pn}**: {count} oy")

            # Sadece admindeyse seçili geçmiş maçı en alttan sikebilme özelliği
            if group["is_admin"]:
                st.markdown("---")
                if st.button("🗑️ Maçı Sil", key=f"del_past_match_{selected_match_id}", use_container_width=True):
                    try:
                        supabase.table("matches").delete().eq("id", selected_match_id).execute()
                        st.success("Geçmiş maç silindi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Maç silinirken hata oluştu: {e}")

            render_match_chat(selected_match_id, user_id, group["id"], is_left)
        else:
            st.info("Henüz oynanmış geçmiş bir maç bulunmuyor.")

    with tab_leaderboard:
        st.subheader("🏆 Grup Puan ve Performans Sıralaması")
        past_matches_data = [m for m in matches_list if str(m["match_date"]) < today_str]
        past_match_ids = [m["id"] for m in past_matches_data]
        
        if past_match_ids:
            stats_res = supabase.table("match_players").select("id, user_id, custom_name, goals, assists, match_id, profiles(full_name)").in_("match_id", past_match_ids).execute()
            
            motm_res = supabase.table("match_motm_votes").select("match_id, voted_player_id, voted_player_name").in_("match_id", past_match_ids).execute()
            motm_data = motm_res.data if motm_res.data else []
            
            match_votes_map = {}
            for vote in motm_data:
                m_id = vote.get("match_id")
                if m_id not in match_votes_map:
                    match_votes_map[m_id] = {}
                
                p_key = vote.get("voted_player_name") or str(vote.get("voted_player_id"))
                match_votes_map[m_id][p_key] = match_votes_map[m_id].get(p_key, 0) + 1

            match_players_map = {}
            for row in (stats_res.data if stats_res.data else []):
                m_id = row.get("match_id")
                if m_id not in match_players_map:
                    match_players_map[m_id] = []
                match_players_map[m_id].append(row)

            motm_award_counts = {}
            for m_id, votes in match_votes_map.items():
                if not votes:
                    continue
                max_votes = max(votes.values())
                top_voted_keys = [k for k, count in votes.items() if count == max_votes]
                
                m_players = match_players_map.get(m_id, [])
                for k in top_voted_keys:
                    resolved_name = k
                    for mp in m_players:
                        d_name = get_player_display_name(mp)
                        u_id_str = str(mp.get("user_id"))
                        p_id_str = str(mp.get("id"))
                        if k == d_name or k == u_id_str or k == p_id_str:
                            resolved_name = d_name
                            break
                    motm_award_counts[resolved_name] = motm_award_counts.get(resolved_name, 0) + 1

            if stats_res.data:
                leaderboard = {}
                for row in stats_res.data:
                    name = get_player_display_name(row)
                    goals = row.get("goals") or 0
                    assists = row.get("assists") or 0
                    
                    motm_wins = motm_award_counts.get(name, 0)
                    
                    if name not in leaderboard:
                        leaderboard[name] = {
                            "Maç Sayısı": 0, 
                            "Toplam Gol": 0, 
                            "Toplam Asist": 0, 
                            "Maçın Adamı": 0,
                            "Toplam Skor Katkısı": 0
                        }
                    
                    leaderboard[name]["Maç Sayısı"] += 1
                    leaderboard[name]["Toplam Gol"] += goals
                    leaderboard[name]["Toplam Asist"] += assists
                    leaderboard[name]["Maçın Adamı"] = motm_wins
                    leaderboard[name]["Toplam Skor Katkısı"] += (goals + assists)

                lb_list = [{"Oyuncu": k, **v} for k, v in leaderboard.items()]
                lb_list = sorted(lb_list, key=lambda x: (x["Toplam Skor Katkısı"], x["Maçın Adamı"]), reverse=True)
                
                st.table(lb_list)
            else:
                st.info("İstatistik bulunamadı.")
        else:
            st.info("Henüz istatistiki veri oluşturacak geçmiş bir maç oynanmadı.")

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
