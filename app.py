import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class InaprocAPIClient:
    def __init__(self, jwt_token: str):
        self.base_url = "https://data.inaproc.id/api"
        self.headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
            "User-Agent": "curl/8.5.0"
        }
    
    def get_ekatalog_data(
        self, 
        use_archive: bool = False,
        limit: int = 5, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mengambil data Paket E-Purchasing dari E-Katalog
        
        Args:
            use_archive: Jika True, gunakan endpoint archive (default: False)
            limit: Jumlah data yang diambil (default: 5)
            start_date: Tanggal mulai filter (format: YYYY-MM-DD)
            end_date: Tanggal akhir filter (format: YYYY-MM-DD)
        
        Returns:
            Dict berisi data E-Katalog dan metadata
        """
        # Pilih endpoint berdasarkan archive atau tidak
        if use_archive:
            endpoint = f"{self.base_url}/v1/ekatalog-archive/paket-e-purchasing"
        else:
            endpoint = f"{self.base_url}/v1/ekatalog/paket-e-purchasing"
        
        params = {"limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error: {e.response.status_code}")
            st.error(f"Response: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Request Error: {str(e)}")
            raise

# Streamlit Page Configuration
st.set_page_config(
    page_title="INAPROC E-Katalog Dashboard",
    page_icon="🛒",
    layout="wide"
)

# Title and Description
st.title("🛒 INAPROC - Dashboard E-Katalog Paket E-Purchasing")
st.markdown("Dashboard untuk menampilkan data Paket E-Purchasing dari E-Katalog INAPROC")

# Sidebar for inputs
st.sidebar.header("⚙️ Konfigurasi")

# JWT Token - Try to load from secrets, fallback to input
try:
    jwt_token = st.secrets["INAPROC_JWT_TOKEN"]
    st.sidebar.success("✅ Token loaded from secrets")
except:
    jwt_token = st.sidebar.text_input(
        "JWT Token INAPROC:",
        type="password",
        help="Masukkan JWT token Anda dari INAPROC"
    )
    if jwt_token:
        st.sidebar.info("💡 Tip: Simpan token di Streamlit Secrets untuk keamanan")

# Endpoint selection
st.sidebar.subheader("📡 Pilih Sumber Data")
use_archive = st.sidebar.radio(
    "Tipe Data:",
    options=[False, True],
    format_func=lambda x: "📦 E-Katalog (Aktif)" if not x else "📚 E-Katalog Archive",
    help="Pilih antara data aktif atau archive"
)

# Data limit
limit = st.sidebar.number_input(
    "Jumlah Data:",
    min_value=1,
    max_value=1000,
    value=10,
    step=5,
    help="Jumlah data yang akan diambil"
)

# Date filters
use_date_filter = st.sidebar.checkbox("Gunakan Filter Tanggal")

start_date = None
end_date = None

if use_date_filter:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date_input = st.date_input(
            "Dari Tanggal:",
            value=datetime.now() - timedelta(days=30)
        )
        start_date = start_date_input.strftime("%Y-%m-%d")
    
    with col2:
        end_date_input = st.date_input(
            "Sampai Tanggal:",
            value=datetime.now()
        )
        end_date = end_date_input.strftime("%Y-%m-%d")

# Fetch button
fetch_button = st.sidebar.button("🔄 Ambil Data", type="primary", use_container_width=True)

# Main content
if not jwt_token:
    st.info("👈 Silakan masukkan JWT Token di sidebar untuk memulai")
    st.warning("""
    **Untuk menyimpan token secara permanen:**
    1. Buka Settings app Anda di Streamlit Cloud
    2. Klik tab "Secrets"
    3. Tambahkan:
    ```
    INAPROC_JWT_TOKEN = "your_token_here"
    ```
    4. Save dan restart app
    """)
else:
    if fetch_button:
        try:
            with st.spinner("Mengambil data dari INAPROC..."):
                # Create API client
                client = InaprocAPIClient(jwt_token)
                
                # Fetch data
                ekatalog_data = client.get_ekatalog_data(
                    use_archive=use_archive,
                    limit=limit,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Store in session state
                st.session_state['ekatalog_data'] = ekatalog_data
                st.session_state['last_fetch'] = datetime.now()
                st.session_state['is_archive'] = use_archive
        
        except Exception as e:
            st.error(f"Gagal mengambil data: {str(e)}")

# Display data if available
if 'ekatalog_data' in st.session_state:
    ekatalog_data = st.session_state['ekatalog_data']
    
    # Success message with source indicator
    source_type = "Archive" if st.session_state.get('is_archive', False) else "Aktif"
    st.success(f"✅ Berhasil mengambil data dari E-Katalog ({source_type})! Terakhir diperbarui: {st.session_state['last_fetch'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Metadata
    meta = ekatalog_data.get('meta', {})
    if meta:
        st.subheader("📈 Informasi Data")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Data", len(ekatalog_data.get('data', [])))
        with col2:
            st.metric("Page", meta.get('page', 'N/A'))
        with col3:
            st.metric("Per Page", meta.get('per_page', 'N/A'))
        with col4:
            st.metric("Total Records", meta.get('total', 'N/A'))
    
    # Convert to DataFrame
    if 'data' in ekatalog_data and ekatalog_data['data']:
        df = pd.DataFrame(ekatalog_data['data'])
        
        st.subheader("📋 Data Paket E-Purchasing")
        
        # Search functionality
        search = st.text_input("🔍 Cari data:", placeholder="Ketik untuk mencari...")
        
        if search:
            # Search across all columns (convert to string first)
            mask = df.astype(str).apply(lambda row: row.str.contains(search, case=False).any(), axis=1)
            filtered_df = df[mask]
            st.write(f"Menampilkan {len(filtered_df)} dari {len(df)} data")
        else:
            filtered_df = df
        
        # Display dataframe with all features
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=400
        )
        
        # Download buttons
        st.subheader("💾 Unduh Data")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"inaproc_ekatalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # JSON download
            import json
            json_str = json.dumps(ekatalog_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"inaproc_ekatalog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Show raw data option
        with st.expander("🔍 Lihat Raw Data (JSON)"):
            st.json(ekatalog_data)
    else:
        st.warning("Tidak ada data yang ditemukan")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Tentang")
st.sidebar.info("""
Dashboard ini menggunakan API INAPROC untuk menampilkan data 
Paket E-Purchasing dari E-Katalog. 

**Endpoint yang tersedia:**
- E-Katalog (Aktif)
- E-Katalog Archive

Hubungi administrator untuk mendapatkan JWT Token.
""")
