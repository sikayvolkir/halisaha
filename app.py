import streamlit as st
from supabase import create_client, Client
import pandas as pd
import urllib.parse

# Page Configuration
st.set_page_config(
    page_title="Halısaha Takip Uygulaması",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Supabase Client
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Session State Initialization
if "user" not in st.session_state:
    st.session_state.user = None
if "profile" not in st.session_state:
    st.session_state.profile = None

def get_profile_name(profile_data):
    if not profile_data:
        return "Bilinmeyen Oyuncu"
    if isinstance(profile_data, list) and len(profile_data) > 0:
        return profile_data[0].get("full_name", "Bilinmeyen Oyuncu")
    if isinstance(profile_data, dict):
        return profile_data.get("full_name", "Bilinmeyen Oyuncu")
    return "Bilinmeyen Oyuncu"

# URL Parameters Check (e.g. ?group_id=...)
query_params = st.query_params
auto_group_id = query_params.get("group_id", None)

# =========================================================
# AUTHENTICATION SCREEN
# =========================================================
if st.session_state.user is None:
    st.title("⚽ Halısaha Takip Uygulaması")
    st.write("Maçlarınızı düzenleyin, kadroları kurun, oyuncu istatistiklerini ve reytinglerini takip edin!")

    auth_tab1, auth_tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])

    with auth_tab1:
        st.subheader("Giriş Yap")
        login_email = st.text_input("E-posta Adresi", key="login_email")
        login_password = st.text_input("Şifre", type="password", key="login_password")
        
        if st.button("Giriş Yap", type="primary"):
            if login_email and login_password:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": login_email,
                        "password": login_password
                    })
                    st.session_state.user = res.user
                    prof = supabase.table("profiles").select("*").eq("id", res.user.id).single().execute()
                    st.session_state.profile = prof.data
                    st.success("Başarıyla giriş yapıldı!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Giriş hatası: {e}")
            else:
                st.warning("Lütfen e-posta ve şifrenizi girin.")

    with auth_tab2:
        st.subheader("Yeni Hesap Oluştur")
        reg_name = st.text_input("Ad Soyad", key="reg_name")
        reg_email = st.text_input("E-posta Adresi", key="reg_email")
        reg_password = st.text_input("Şifre", type="password", key="reg_password")
        
        if st.button("Kayıt Ol"):
            if reg_name and reg_email and reg_password:
                try:
                    res = supabase.auth.sign_up({
                        "email": reg_email,
                        "password": reg_password,
                        "options": {
                            "data": {
                                "full_name": reg_name
                            }
                        }
                    })
                    st.success("Kayıt başarılı! Şimdi Giriş Yap sekmesinden oturum açabilirsiniz.")
                except Exception as e:
                    st.error(f"Kayıt hatası: {e}")
            else:
                st.warning("Lütfen tüm alanları doldurun.")
    st.stop()

# =========================================================
# MAIN DASHBOARD (LOGGED IN)
# =========================================================
user = st.session_state.user
profile = st.session_state.profile

# Sidebar Navigation & User Info
with st.sidebar:
    st.write(f"👋 **Hoş geldin, {profile.get('full_name', 'Oyuncu')}**")
    st.caption(f"📧 {user.email}")
    
    if st.button("🚪 Çıkış Yap"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.profile = None
        st.rerun()

    st.divider()
    st.subheader("➕ Yeni Grup Oluştur")
    new_group_name = st.text_input("Grup Adı", key="new_group_name")
    if st.button("Grup Oluştur"):
        if new_group_name.strip():
            try:
                # 1. Create group
                g_res = supabase.table("groups").insert({"name": new_group_name.strip(), "created_by": user.id}).execute()
                created_group_id = g_res.data[0]["id"]
                # 2. Add creator as admin member
                supabase.table("group_members").insert({"group_id": created_group_id, "user_id": user.id, "is_admin": True}).execute()
                st.success(f"'{new_group_name}' grubu oluşturuldu!")
                st.rerun()
            except Exception as e:
                st.error(f"Grup oluşturulurken hata: {e}")
        else:
            st.warning("Lütfen bir grup adı girin.")

# Fetch User Groups
user_groups_res = supabase.table("group_members").select("is_admin, is_left, groups(id, name)").eq("user_id", user.id).execute()
user_groups = [
    {
        "id": item["groups"]["id"],
        "name": item["groups"]["name"],
        "is_admin": item["is_admin"],
        "is_left": item["is_left"]
    }
    for item in user_groups_res.data if item.get("groups")
]

st.title("⚽ Halısaha Yönetim Paneli")

# Automatic Group Join Request from URL parameter
if auto_group_id:
    try:
        # Check if already a member
        existing_m = supabase.table("group_members").eq("group_id", auto_group_id).eq("user_id", user.id).execute()
        if not existing_m.data:
            st.info(f"🔗 Bağlantı ile bir gruba davet edildiniz (Grup ID: {auto_group_id}).")
            if st.button("Gruba Katılma İsteği Gönder"):
                supabase.table("group_join_requests").insert({"group_id": auto_group_id, "user_id": user.id, "status": "pending"}).execute()
                st.success("Katılım isteğiniz grup yöneticisine iletildi!")
                st.query_params.clear()
                st.rerun()
    except Exception as e:
        pass

if not user_groups:
    st.info("Henüz herhangi bir gruba üye değilsiniz. Sol taraftaki menüden yeni bir grup oluşturabilir veya size gelen davet linkini kullanabilirsiniz.")
    st.stop()

# Select Active Group
group_options = {g["name"]: g for g in user_groups}
selected_group_name = st.selectbox("🎯 İşlem Yapmak İstediğiniz Grubu Seçin:", list(group_options.keys()))
group = group_options[selected_group_name]
is_left = group["is_left"]

if is_left:
    st.warning("⚠️ Bu gruptan ayrılmış durumdasınız. Geçmiş verileri görüntüleyebilirsiniz ancak yeni işlem yapamazsınız.")

st.divider()

# Navigation Tabs
tab_matches, tab_ratings, tab_members = st.tabs(["🏟️ Maçlar & Kadrolar", "⭐ Oyuncu Reytingleri", "👥 Grup Üyeleri & Davet"])

# =========================================================
# TAB: MAÇLAR & KADROLAR
# =========================================================
with tab_matches:
    if group["is_admin"] and not is_left:
        with st.expander("➕ Yeni Maç Ekle (Yönetici)"):
            with st.form("new_match_form"):
                m_date = st.date_input("Maç Tarihi")
                m_time = st.time_input("Maç Saati")
                m_location = st.text_input("Halısaha / Saha Adı", value="Belediye Halısaha")
                m_cost = st.number_input("Toplam Saha Ücreti (TL)", min_value=0.0, step=50.0)
                
                submit_match = st.form_submit_button("Maçı Oluştur ve Duyur")
                if submit_match:
                    try:
                        match_datetime = f"{m_date}T{m_time}"
                        supabase.table("matches").insert({
                            "group_id": group["id"],
                            "match_date": match_datetime,
                            "location": m_location,
                            "total_cost": m_cost,
                            "status": "upcoming"
                        }).execute()
                        st.success("Yeni maç başarıyla eklendi!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Maç eklenirken hata: {e}")

    # List Matches
    matches_res = supabase.table("matches").select("*").eq("group_id", group["id"]).order("match_date", desc=True).execute()
    matches = matches_res.data

    if not matches:
        st.info("Bu grupta henüz planlanmış bir maç yok.")
    else:
        for m in matches:
            m_status = "🟢 Gelecek Maç" if m["status"] == "upcoming" else "🔴 Tamamlandı"
            with st.expander(f"📅 {m['match_date'][:16].replace('T', ' ')} - {m['location']} ({m_status})", expanded=(m["status"] == "upcoming")):
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.write(f"**Konum:** {m['location']}")
                    st.write(f"**Toplam Ücret:** {m['total_cost']} TL")
                    st.write(f"**Durum:** {m_status}")
                    
                    # Availability Status
                    att_res = supabase.table("match_attendance").select("status, profiles(full_name)").eq("match_id", m["id"]).execute()
                    atts = att_res.data
                    
                    coming = [get_profile_name(a.get("profiles")) for a in atts if a["status"] == "coming"]
                    not_coming = [get_profile_name(a.get("profiles")) for a in atts if a["status"] == "not_coming"]
                    
                    st.write(f"✅ **Geliyor ({len(coming)}):** {', '.join(coming) if coming else 'Henüz kimse yok'}")
                    st.write(f"❌ **Gelmiyor ({len(not_coming)}):** {', '.join(not_coming) if not_coming else 'Henüz kimse yok'}")

                    if m["status"] == "upcoming" and not is_left:
                        st.write("---")
                        st.write("**Katılım Durumunu Güncelle:**")
                        c_btn1, c_btn2 = st.columns(2)
                        if c_btn1.button("✅ Geliyorum", key=f"yes_{m['id']}"):
                            supabase.table("match_attendance").upsert({
                                "match_id": m["id"],
                                "user_id": user.id,
                                "status": "coming"
                            }).execute()
                            st.rerun()
                        if c_btn2.button("❌ Gelmiyorum", key=f"no_{m['id']}"):
                            supabase.table("match_attendance").upsert({
                                "match_id": m["id"],
                                "user_id": user.id,
                                "status": "not_coming"
                            }).execute()
                            st.rerun()

                with col2:
                    st.subheader("📋 Kadro & Takımlar")
                    squad_res = supabase.table("match_squads").select("team, profiles(full_name)").eq("match_id", m["id"]).execute()
                    squad = squad_res.data
                    
                    team_a = [get_profile_name(s.get("profiles")) for s in squad if s["team"] == "A"]
                    team_b = [get_profile_name(s.get("profiles")) for s in squad if s["team"] == "B"]
                    
                    sq_col1, sq_col2 = st.columns(2)
                    with sq_col1:
                        st.markdown("### 🔴 A Takımı")
                        for p in team_a:
                            st.write(f"- {p}")
                    with sq_col2:
                        st.markdown("### 🔵 B Takımı")
                        for p in team_b:
                            st.write(f"- {p}")

                    if group["is_admin"] and m["status"] == "upcoming" and not is_left:
                        st.write("---")
                        st.write("**⚙️ Otomatik Kadro Kur (Admin):**")
                        if st.button("🎲 Gelenlerden Dengeli Kadro Yap", key=f"squad_btn_{m['id']}"):
                            coming_users = [a["profiles"]["full_name"] for a in atts if a["status"] == "coming" and a.get("profiles")]
                            coming_ids = [a["user_id"] for a in atts if a["status"] == "coming"]
                            
                            if len(coming_ids) < 2:
                                st.warning("Kadro kurmak için en az 2 kişi 'Geliyorum' demelidir.")
                            else:
                                import random
                                random.shuffle(coming_ids)
                                half = len(coming_ids) // 2
                                team_a_ids = coming_ids[:half]
                                team_b_ids = coming_ids[half:]
                                
                                supabase.table("match_squads").delete().eq("match_id", m["id"]).execute()
                                
                                squad_inserts = []
                                for uid in team_a_ids:
                                    squad_inserts.append({"match_id": m["id"], "user_id": uid, "team": "A"})
                                for uid in team_b_ids:
                                    squad_inserts.append({"match_id": m["id"], "user_id": uid, "team": "B"})
                                
                                supabase.table("match_squads").insert(squad_inserts).execute()
                                st.success("Kadrolar rastgele/dengeli dağıtıldı!")
                                st.rerun()

# =========================================================
# TAB: OYUNCU REYTINGLERI
# =========================================================
with tab_ratings:
    st.subheader("⭐ Oyuncu Reyting ve Oylama Sistemi")
    st.write("Son maçtaki oyuncuların performanslarını 1-10 üzerinden değerlendirin.")
    
    ratings_res = supabase.table("ratings").select("rated_user_id, score").execute()
    if ratings_res.data:
        df_ratings = pd.DataFrame(ratings_res.data)
        profiles_res = supabase.table("profiles").select("id, full_name").execute()
        prof_map = {p["id"]: p["full_name"] for p in profiles_res.data}
        
        df_ratings["Oyuncu"] = df_ratings["rated_user_id"].map(prof_map)
        avg_ratings = df_ratings.groupby("Oyuncu")["score"].agg(["mean", "count"]).reset_index()
        avg_ratings.columns = ["Oyuncu Adı", "Ortalama Puan", "Oy Sayısı"]
        avg_ratings["Ortalama Puan"] = avg_ratings["Ortalama Puan"].round(2)
        
        st.dataframe(avg_ratings.sort_values(by="Ortalama Puan", ascending=False), use_container_width=True)
    else:
        st.info("Henüz oy kullanılmış bir değerlendirme bulunmuyor.")

    st.divider()
    st.write("### 📝 Oy Kullan")
    all_members = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).execute()
    member_options = {get_profile_name(m.get("profiles")): m["user_id"] for m in all_members.data if m.get("user_id") != user.id}
    
    if member_options:
        selected_player = st.selectbox("Değerlendirilecek Oyuncu", list(member_options.keys()))
        score_val = st.slider("Puan (1 - 10)", min_value=1, max_value=10, value=7)
        
        if st.button("Puanı Kaydet"):
            target_uid = member_options[selected_player]
            try:
                supabase.table("ratings").upsert({
                    "evaluator_id": user.id,
                    "rated_user_id": target_uid,
                    "score": score_val
                }).execute()
                st.success(f"{selected_player} için {score_val} puan verildi!")
                st.rerun()
            except Exception as e:
                st.error(f"Puan verilirken hata oluştu: {e}")

# =========================================================
# TAB: GRUP ÜYELERİ & DAVET (WHATSAPP ENTEGRASYONLU)
# =========================================================
with tab_members:
    st.subheader("📲 Gruba Davet Linki & WhatsApp Paylaşımı")
    
    # Live Application Public URL (Update with your actual deployed app URL if different)
    app_base_url = "https://halisaha-takip.streamlit.app"
    invite_link = f"{app_base_url}/?group_id={group['id']}"
    
    # WhatsApp Pre-filled Message Text
    share_text = f"⚽ *{group['name']}* halısaha grubuna davet edildin!\n\nAşağıdaki bağlantıya tıklayarak gruba katılabilir ve maç kadrolarını takip edebilirsin:\n{invite_link}"
    
    # URL Encoding for WhatsApp Web/App
    encoded_text = urllib.parse.quote(share_text)
    whatsapp_url = f"https://api.whatsapp.com/send?text={encoded_text}"
    
    # Layout UI for Share Button
    c_link, c_wa = st.columns([2, 1])
    
    with c_link:
        st.text_input("Grup Katılım Bağlantısı", value=invite_link, disabled=True, key=f"inv_input_{group['id']}")
        
    with c_wa:
        st.markdown(
            f'''
            <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
                <button style="
                    background-color: #25D366;
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                    cursor: pointer;
                    width: 100%;
                    margin-top: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;">
                    📲 WhatsApp ile Paylaş
                </button>
            </a>
            ''',
            unsafe_allow_html=True
        )
        
    st.caption("💡 Bu bağlantıya tıklayan kişiler doğrudan uygulamanızdaki bu gruba katılma isteği gönderebilir.")
    st.divider()

    # List Group Members
    st.subheader("👥 Grup Üyeleri")
    members = supabase.table("group_members").select("is_admin, is_left, profiles(full_name)").eq("group_id", group["id"]).execute()
    
    for m in members.data:
        name = get_profile_name(m.get("profiles"))
        status = " (Ayrıldı)" if m.get("is_left") else ""
        role = "⭐ Admin" if m["is_admin"] else "🏃 Oyuncu"
        st.write(f"- **{name}** ({role}){status}")
        
    # Pending Join Requests (Admin Only)
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
        else:
            st.caption("Bekleyen katılım isteği bulunmuyor.")
