import streamlit as st
import requests
import urllib.parse
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
# Importação do GPS
try:
    from streamlit_js_eval import get_geolocation
    GPS_INSTALADO = True
except ImportError:
    GPS_INSTALADO = False

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="MotoFrete", page_icon="🏍️", layout="centered")

# --- SUAS COORDENADAS ---
LOJA_LAT = -15.752369
LOJA_LON = -48.324535
CIDADE_PADRAO = "Cocalzinho de Goiás"

# --- PREÇOS ---
TAXA_MINIMA = 5.00
KM_INCLUSO = 5.0
PRECO_KM_EXTRA = 0.75

# --- FERRAMENTAS ---
geolocator = Nominatim(user_agent="motofrete_gps_final_v11")

# --- FUNÇÕES ---
def limpar_memoria():
    st.session_state['resultado'] = None
    st.rerun()

def obter_rota_osrm(lat_dest, lon_dest):
    start = f"{LOJA_LON},{LOJA_LAT}"
    end = f"{lon_dest},{lat_dest}"
    url = f"http://router.project-osrm.org/route/v1/driving/{start};{end}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            route = data['routes'][0]
            dist_km = route['distance'] / 1000
            caminho = [[p[1], p[0]] for p in route['geometry']['coordinates']]
            return caminho, dist_km
    except:
        return None, None

def calcular_valor(dist_km):
    if dist_km <= KM_INCLUSO:
        return TAXA_MINIMA
    else:
        return TAXA_MINIMA + ((dist_km - KM_INCLUSO) * PRECO_KM_EXTRA)

def processar_calculo(lat, lon, end_texto, ref_texto):
    caminho, dist = obter_rota_osrm(lat, lon)
    
    if caminho is None:
        dist = geodesic((LOJA_LAT, LOJA_LON), (lat, lon)).km * 1.3
        caminho = [[LOJA_LAT, LOJA_LON], [lat, lon]]
    
    valor = calcular_valor(dist)
    
    st.session_state['resultado'] = {
        'lat': lat, 'lon': lon,
        'dist': dist, 'val': valor,
        'caminho': caminho,
        'msg_end': end_texto,
        'msg_ref': ref_texto
    }

# --- INICIALIZAÇÃO ---
if 'resultado' not in st.session_state:
    st.session_state['resultado'] = None

# ==========================================
#              TELA DE ENTRADA
# ==========================================
st.title("🏍️ Solicitar Entrega")
st.markdown("---")

if st.session_state['resultado'] is None:
    
    st.info("Preencha os dados para o entregador:")
    
    # 1. CAMPOS DE TEXTO
    endereco = st.text_input("Endereço Completo:", placeholder="Ex: Rua das Flores, 10, Centro")
    referencia = st.text_input("Ponto de Referência:", placeholder="Ex: Portão cinza")
    
    st.write("---")
    st.markdown("### 📍 Localização (GPS)")
    st.caption("Clique no botão abaixo para aumentar a precisão:")
    
    # 2. BOTÃO GPS (CORRIGIDO: SEM O ARGUMENTO 'LABEL')
    lat_gps = None
    lon_gps = None
    
    if GPS_INSTALADO:
        gps_data = get_geolocation(component_key='gps_unico') # <--- CORREÇÃO AQUI
        
        if gps_data:
            lat_gps = gps_data['coords']['latitude']
            lon_gps = gps_data['coords']['longitude']
            st.success("✅ GPS Localizado com sucesso!")
    else:
        st.error("Erro: Biblioteca GPS não instalada.")
    
    st.write("")
    
    # 3. BOTÃO CALCULAR
    if st.button("CALCULAR FRETE 🚀", type="primary", use_container_width=True):
        
        if not endereco:
            st.warning("⚠️ Escreva o endereço antes de calcular.")
        else:
            lat_final = None
            lon_final = None
            
            # Prioridade: GPS
            if lat_gps and lon_gps:
                lat_final = lat_gps
                lon_final = lon_gps
            
            # Se não tiver GPS, vai pelo texto
            else:
                with st.spinner("Buscando endereço pelo texto (GPS desligado)..."):
                    try:
                        busca = f"{endereco}, {CIDADE_PADRAO}"
                        loc = geolocator.geocode(busca)
                        if loc:
                            lat_final = loc.latitude
                            lon_final = loc.longitude
                    except:
                        pass
            
            if lat_final and lon_final:
                processar_calculo(lat_final, lon_final, endereco, referencia)
                st.rerun()
            else:
                st.error("❌ Não conseguimos te localizar. Tente ativar o GPS e clicar no botão novamente.")

# ==========================================
#              TELA DE RESULTADO
# ==========================================
else:
    res = st.session_state['resultado']
    
    st.success("✅ Rota Calculada!")
    
    m = folium.Map(location=[LOJA_LAT, LOJA_LON], zoom_start=14)
    folium.PolyLine(res['caminho'], color="blue", weight=5, opacity=0.7).add_to(m)
    folium.Marker([LOJA_LAT, LOJA_LON], popup="LOJA", icon=folium.Icon(color="green", icon="home")).add_to(m)
    folium.Marker([res['lat'], res['lon']], popup="VOCÊ", icon=folium.Icon(color="red", icon="flag")).add_to(m)
    st_folium(m, width=700, height=400)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Distância", f"{res['dist']:.2f} km")
    c2.metric("VALOR", f"R$ {res['val']:.2f}")
    c3.metric("Tempo", f"{int(res['dist']*2)} min")
    
    SEU_ZAP = "5561998800459" # <--- SEU NÚMERO
    
    msg = f"""Olá! Solicito entrega:\n\n📍 {res['msg_end']}\n👁️ {res['msg_ref']}\n\n💰 Valor: R$ {res['val']:.2f}\n🗺️ Maps: http://googleusercontent.com/maps.google.com/4{res['lat']},{res['lon']}"""
    
    link = f"https://wa.me/{SEU_ZAP}?text={urllib.parse.quote(msg)}"
    
    st.link_button("📲 ENVIAR PEDIDO (WhatsApp)", link, use_container_width=True)
    
    st.write("")
    if st.button("⬅️ Nova Pesquisa"):
        limpar_memoria()