import streamlit as st
from supabase import create_client, Client

# ---------------------------------------------------------
# Sayfa Konfigürasyonu & Tema (Yeşil-Siyah-Beyaz)
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

# ---------------------------------------------------------
# Kimlik Doğrulama Ekranı (Giriş / Kayıt)
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
# Ana Sayfa (Grup Seçimi / Yeni Grup Oluşturma)
# ---------------------------------------------------------
def main_dashboard():
    st.markdown("<h1 class='main-title'>⚽ HALISAHA GRUPLARIM</h1>", unsafe_allow_html=True)
    user_id = st.session_state.user.id
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Dahil Olduğunuz Gruplar")
        # Kullanıcının dahil olduğu grupları çek
        memberships = supabase.table("group_members").select("group_id, is_admin, groups(id, name)").eq("user_id", user_id).execute()
        
        if memberships.data:
            for item in memberships.data:
                group = item["groups"]
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
                    # 1. Grubu oluştur
                    group_res = supabase.table("groups").insert({
                        "name": new_group_name.strip(),
                        "created_by": user_id
                    }).execute()
                    
                    new_group_id = group_res.data[0]["id"]
                    
                    # 2. Kurucuyu Admin olarak gruba ekle
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
# Grup Detay Sayfası (Maç Oluştur, Eski Maçlar, Puanlar)
# ---------------------------------------------------------
def group_detail():
    group = st.session_state.selected_group
    user_id = st.session_state.user.id
    
    if st.button("← Ana Sayfaya Dön"):
        st.session_state.selected_group = None
        st.rerun()
        
    st.markdown(f"<h1 class='main-title'>⚽ {group['name']}</h1>", unsafe_allow_html=True)
    
    # Yönetici Atama Seçeneği (Yalnızca Admin İçin)
    if group["is_admin"]:
        with st.expander("🛠️ Admin Paneli: Yeni Admin Ata"):
            all_members = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).eq("is_admin", False).execute()
            if all_members.data:
                member_opts = {m["profiles"]["full_name"]: m["user_id"] for m in all_members.data}
                selected_member = st.selectbox("Admin yapmak istediğiniz üye:", list(member_opts.keys()))
                if st.button("Admin Yetkisi Ver"):
                    supabase.table("group_members").update({"is_admin": True}).eq("group_id", group["id"]).eq("user_id", member_opts[selected_member]).execute()
                    st.success(f"{selected_member} artık admin!")
                    st.rerun()
            else:
                st.write("Tüm üyeler zaten admin ya da başka üye yok.")

    # Ekran Sekmeleri
    tab1, tab2, tab3 = st.tabs(["➕ Yeni Maç Oluştur", "📜 Eski Maçlar & İstatistikler", "🏆 Puan Sıralaması"])
    
    # ------------------ TAB 1: Yeni Maç Oluştur ------------------
    with tab1:
        st.subheader("Yeni Maç Planla")
        if group["is_admin"]:
            match_date = st.date_input("Maç Tarihi")
            location = st.text_input("Halı Saha / Saha Adı", value="Merkez Halı Saha")
            
            # Üyeleri Listele
            members_data = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).execute()
            player_dict = {m["profiles"]["full_name"]: m["user_id"] for m in members_data.data}
            
            selected_players = st.multiselect("Kadroya Alınacak Oyuncular", options=list(player_dict.keys()), default=list(player_dict.keys()))
            
            if st.button("Maçı Oluştur ve Bildir"):
                if selected_players:
                    # Maç ekle
                    match_res = supabase.table("matches").insert({
                        "group_id": group["id"],
                        "match_date": str(match_date),
                        "location": location,
                        "created_by": user_id
                    }).execute()
                    
                    match_id = match_res.data[0]["id"]
                    
                    # Oyuncuları maça ekle
                    players_to_insert = [{"match_id": match_id, "user_id": player_dict[p]} for p in selected_players]
                    supabase.table("match_players").insert(players_to_insert).execute()
                    
                    st.success("Maç başarıyla oluşturuldu ve oyuncular kadroya eklendi!")
                else:
                    st.warning("Lütfen en az bir oyuncu seçin.")
        else:
            st.info("Sadece grup adminleri yeni maç oluşturabilir.")

    # ------------------ TAB 2: Eski Maçlar ------------------
    with tab2:
        st.subheader("Grup Maçları")
        matches = supabase.table("matches").select("*").eq("group_id", group["id"]).order("match_date", desc=True).execute()
        
        if matches.data:
            match_options = {f"{m['match_date']} - {m['location']}": m["id"] for m in matches.data}
            selected_match_label = st.selectbox("Bir Maç Seçin:", list(match_options.keys()))
            selected_match_id = match_options[selected_match_label]
            
            # Maç Oyuncularını Getir
            players_in_match = supabase.table("match_players").select("user_id, goals, assists, profiles(full_name)").eq("match_id", selected_match_id).execute()
            
            st.write("#### 📊 Maç Kadrosu ve Performans")
            
            # İstatistik / Skor Tablosu
            table_data = []
            for p in players_in_match.data:
                table_data.append({
                    "Oyuncu": p["profiles"]["full_name"],
                    "Gol": p["goals"],
                    "Asist": p["assists"]
                })
            st.table(table_data)

            # --- KENDİ İSTATİSTİĞİNİ GİRME (GOL / ASİST) ---
            st.write("---")
            st.write("#### ⚽ Kendi Gol/Asist Sayını Güncelle")
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
                    if st.button("Kaydet"):
                        supabase.table("match_players").update({"goals": my_goals, "assists": my_assists}).eq("match_id", selected_match_id).eq("user_id", user_id).execute()
                        st.success("İstatistikler güncellendi!")
                        st.rerun()
            else:
                st.caption("Bu maçın kadrosunda yer almıyorsunuz.")

            # --- PUANLAMA VE MVP OYLAMASI ---
            st.write("---")
            st.write("#### ⭐ Oyuncuları Puanla ve Maçın Oyuncusunu (MVP) Seç")
            
            other_players = [p for p in players_in_match.data if p["user_id"] != user_id]
            if other_players:
                other_player_opts = {p["profiles"]["full_name"]: p["user_id"] for p in other_players}
                rated_user_name = st.selectbox("Puan Verilecek Oyuncu:", list(other_player_opts.keys()))
                score = st.slider("Puan (1-10):", 1, 10, 7)
                
                if st.button("Puanı Gönder"):
                    try:
                        supabase.table("match_ratings").insert({
                            "match_id": selected_match_id,
                            "rater_id": user_id,
                            "rated_user_id": other_player_opts[rated_user_name],
                            "rating": score
                        }).execute()
                        st.success(f"{rated_user_name} için puan kaydedildi!")
                    except Exception:
                        st.error("Bu oyuncuyu bu maç için zaten puanladınız!")

                # MVP Oylaması
                st.write("##### 🏅 Maçın Oyuncusu (MVP) Oyu")
                all_player_opts = {p["profiles"]["full_name"]: p["user_id"] for p in players_in_match.data}
                mvp_choice = st.selectbox("Maçın Oyuncusu Adayın:", list(all_player_opts.keys()), key="mvp_select")
                if st.button("MVP Oyunu Kullan"):
                    try:
                        supabase.table("match_mvp_votes").insert({
                            "match_id": selected_match_id,
                            "voter_id": user_id,
                            "voted_user_id": all_player_opts[mvp_choice]
                        }).execute()
                        st.success(f"MVP oyunuz {mvp_choice} isimli oyuncuya iletildi!")
                    except Exception:
                        st.error("Bu maç için zaten MVP oyunu kullandınız!")
        else:
            st.info("Bu gruba ait henüz yapılmış bir maç bulunmuyor.")

    # ------------------ TAB 3: Puan Sıralaması ------------------
    with tab3:
        st.subheader("🏆 Genel İstatistikler ve Sıralama")
        
        # Tüm maç istatistiklerini derle
        all_players = supabase.table("group_members").select("user_id, profiles(full_name)").eq("group_id", group["id"]).execute()
        
        leaderboard = []
        for p in all_players.data:
            p_id = p["user_id"]
            p_name = p["profiles"]["full_name"]
            
            # Toplam Gol ve Asist
            stats = supabase.table("match_players").select("goals, assists").eq("user_id", p_id).execute()
            tot_goals = sum([item["goals"] for item in stats.data]) if stats.data else 0
            tot_assists = sum([item["assists"] for item in stats.data]) if stats.data else 0
            
            # Ortalama Puan
            ratings = supabase.table("match_ratings").select("rating").eq("rated_user_id", p_id).execute()
            if ratings.data:
                avg_rating = round(sum([r["rating"] for r in ratings.data]) / len(ratings.data), 2)
            else:
                avg_rating = 0.0
                
            # MVP Seçilme Sayısı
            mvp_count = len(supabase.table("match_mvp_votes").select("id").eq("voted_user_id", p_id).execute().data)
            
            leaderboard.append({
                "Oyuncu": p_name,
                "Toplam Gol": tot_goals,
                "Toplam Asist": tot_assists,
                "Ortalama Puan": avg_rating,
                "Maçın Oyuncusu (MVP)": mvp_count
            })
            
        # Tabloyu Gol Sayısına Göre Sırala
        leaderboard = sorted(leaderboard, key=lambda x: x["Toplam Gol"], reverse=True)
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
                  
