import streamlit as st

def inject_theme():
    """
    Injects a premium UI theme into Streamlit.
    Reads 'dark_mode' from st.session_state (default True).
    Features: Glassmorphism, modern typography (Inter), rounded corners, soft shadows, 
    and micro-animations on interactive elements.
    """
    dark_mode = st.session_state.get("global_dark_mode", True)
    
    if dark_mode:
        bg_color = "#0e1117"
        text_color = "#fafafa"
        card_bg = "rgba(255, 255, 255, 0.05)"
        border_color = "rgba(255, 255, 255, 0.1)"
        hover_shadow = "rgba(0, 150, 255, 0.2)"
        border_hover = "rgba(0, 150, 255, 0.5)"
    else:
        bg_color = "#f4f6f8"
        text_color = "#1a1a1a"
        card_bg = "rgba(255, 255, 255, 0.7)"
        border_color = "rgba(0, 0, 0, 0.05)"
        hover_shadow = "rgba(0, 150, 255, 0.15)"
        border_hover = "rgba(0, 150, 255, 0.4)"

    css = f"""
    <style>
        /* Import premium font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Apply font to everything */
        html, body, [class*="st-"] {{
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Main background & text */
        [data-testid="stAppViewContainer"] {{
            background-color: {bg_color};
            color: {text_color};
            transition: background-color 0.3s ease;
        }}
        
        /* Sidebar Glassmorphism & Text Colors */
        [data-testid="stSidebar"] {{
            background-color: {card_bg};
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-right: 1px solid {border_color};
        }}
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebarNav"] a,
        [data-testid="stSidebarNav"] span {{
            color: {text_color} !important;
        }}
        [data-testid="stSidebarNav"] svg {{
            fill: {text_color} !important;
            stroke: {text_color} !important;
        }}
        
        /* Glassmorphism for Metrics, Dataframes, and Expanders */
        [data-testid="stMetric"], .stDataFrame, [data-testid="stExpander"] {{
            background-color: {card_bg} !important;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid {border_color} !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
            transition: all 0.3s ease-in-out;
        }}
        
        /* Metrics Hover Animation */
        [data-testid="stMetric"]:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 20px {hover_shadow};
            border-color: {border_hover} !important;
        }}
        
        /* Button styling */
        div.stButton > button {{
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border: 1px solid {border_color} !important;
        }}
        
        div.stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px {hover_shadow};
            border-color: {border_hover} !important;
            color: {text_color} !important;
        }}
        
        /* Tabs styling */
        [data-testid="stTabs"] button {{
            font-weight: 500;
            padding-bottom: 0.5rem;
        }}
        
        /* Cleaner Header */
        header {{
            background-color: transparent !important;
        }}
        
        /* Headers gradient */
        h1, h2, h3 {{
            letter-spacing: -0.02em;
        }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
