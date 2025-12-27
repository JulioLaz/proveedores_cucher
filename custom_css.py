
# === CSS PERSONALIZADO ===
def custom_css():
    return """
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        border-radius: 5px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1000;
    }
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    .insight-box {
        background: #f8f9fa !important;
        border: 1px solid #e9ecef !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #17a2b8 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
        transition: background 0.2s ease;
    }

    .warning-box {
        background: #fff8e1 !important;
        border: 1px solid #ffeaa7 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #ffc107 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
    }

    .success-box {
        background: #e6f4ea !important;
        border: 1px solid #c3e6cb !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin: 0.6rem 0 !important;
        border-left: 5px solid #28a745 !important;
        font-size: 0.93rem;
        line-height: 1.4;
        box-shadow: 0 2px 3px rgba(0, 0, 0, 0.04);
    }

    /* ═══════════════════════════════════════════════════════════ */
    /* ESTILOS PARA MÉTRICAS (st.metric) */
    /* ═══════════════════════════════════════════════════════════ */
    
    /* Contenedor de la métrica */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #ffffff 0%, #f3e3a3 100%);
        border: 2px solid #f3c221;
        border-radius: 10px;
        padding: 5px;
        box-shadow: 0 2px 4px rgba(33, 150, 243, 0.15);
        transition: all 0.3s ease;
    }
    
    /* Hover effect en métricas */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(33, 150, 243, 0.25);
        border-color: #1976D2;
    }
    
    /* Valor de la métrica */
    div[data-testid="stMetricValue"] {
        text-align: center;
        justify-content: center;
        align-items: center;
        font-size: 1.2rem;
        font-weight: bold;
        color: #1e3c72;
    }
    
    /* Label de la métrica */
    div[data-testid="stMetricLabel"] {
        text-align: center;
        font-weight: 600;
        color: #555;
        font-size: 0.95rem;
    }
    
    /* Delta (variación) de la métrica */
    div[data-testid="stMetricDelta"] {
        text-align: center;
        justify-content: center;
    }

    /* ═══════════════════════════════════════════════════════════ */
    /* ESTILOS PARA EXPANDERS */
    /* ═══════════════════════════════════════════════════════════ */
    
    /* Background del expander */
    div[data-testid="stExpander"] {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8f4fd 100%);
        border-radius: 8px;
        border: 2px solid #1e3c72;
        padding: 5px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
    }
    
    /* Header del expander (clickeable) */
    div[data-testid="stExpander"] summary {
        background-color: rgba(30, 60, 114, 0.1);
        border-radius: 5px;
        padding: 10px 15px;
        font-weight: 600;
        color: #1e3c72;
        font-size: 1rem;
    }
    
    /* Hover effect en el header */
    div[data-testid="stExpander"] summary:hover {
        background-color: rgba(30, 60, 114, 0.18);
        cursor: pointer;
        transform: translateX(3px);
        transition: all 0.2s ease;
    }
    
    /* Contenido del expander cuando está expandido */
    div[data-testid="stExpander"] details[open] {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 15px;
        margin-top: 8px;
        box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* Efecto de transición suave al abrir/cerrar */
    div[data-testid="stExpander"] details {
        transition: all 0.3s ease-in-out;
    }

    .sidebar .sidebar-content {
        background: #f1f3f4;
        background: black;
    }

    /* 🎯 Estilo personalizado para el contenedor principal */
    .block-container {
        width: 100% !important;
        padding: .5rem 1rem !important;
        min-width: auto !important;
        max-width: initial !important;
    }
            
    /* Estilo personalizado al contenedor específico */
    .st-emotion-cache-16txtl3 {
        padding: 1rem 1rem !important;
    }
            
    /* Estilo personalizado al contenedor específico */
    /* Estilo personalizado al contenedor específico */
    .st-emotion-cache-595tnf {
            height: .5rem !important;
    }

    /* Estilo personalizado btn desplieque de sidebar */
    .st-emotion-cache-595tnf.eu6y2f94 {
        padding: 0.9rem !important;
    }            

    /* Ocultar el header superior de Streamlit */
    header {
        height: 2rem !important;
        min-height: 2rem !important;
        background-color: transparent !important;
        box-shadow: none !important;
        overflow: hidden !important;
        }

    /* ✅ Asegura que el botón de sidebar esté visible */
    [data-testid="collapsedControl"] {
        display: block !important;
        position: fixed !important;
        top: 1rem;
        left: 1rem;
        z-index: 1001;
    }
            
    /* 🎨 Establece un fondo beige claro para toda la app */
    body {
        background-color: #f5f5dc !important; /* beige */
    }

    /* O si querés solo el fondo del contenedor principal */
    .appview-container {
        background-color: #f5f5dc !important;
    }            


    /* Opcional: darle margen interno y borde a todo el gráfico */
    [data-testid="stPlotlyChart"] {
        border-radius: 10px;
        border: 1px solid #ddd;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .main-svg{
        background-color: transparent !important;
            }

    .metric-box {
        background-color: #e8f7fd;
        border-radius: 12px;
        padding: .5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 5px solid #2a5298;
        margin-bottom: .5rem;
    }
            
        @keyframes bounce {
            0%, 100% {
                transform: translateX(0);
            }
            50% {
                transform: translateX(-8px);
            }
        }

        .bounce-info {
            animation: bounce 1s infinite;
            font-weight: bold;
            color: #1e3c72;
            background-color: #e9f5ff;
            border-left: 6px solid #2a5298;
            padding: .5rem;
            border-radius: 8px;
            margin-top: .5rem;
            font-size: 1rem;
        }

        .st-cw {
        padding-top: 0rem !important;
        }

        .st-an {
            padding-top: 0rem !important;
        }            

        .sidebar-box {
            background-color: #ffffff10;
            padding: 1rem;
            border-radius: 10px;
            margin-top: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .sidebar-metric-title {
            font-size: 0.85rem;
            color: #555;
            margin-bottom: 0.2rem;
        }
        .sidebar-metric-value {
            font-size: 1.4rem;
            font-weight: bold;
            color: #1e3c72;
            margin-bottom: 0.8rem;
        }

        /* Estilo marrón vintage para el sidebar */
        section[data-testid="stSidebar"] {
            background-color: #c0e9fafc !important
            color: white;
            padding: 0rem !important;
        }

        /* Opcional: mejorar contraste en los textos del sidebar */
        section[data-testid="stSidebar"] .css-1cpxqw2, /* texto normal */
        section[data-testid="stSidebar"] .css-10trblm, /* encabezados */
        section[data-testid="stSidebar"] .st-emotion-cache-1wmy9hl {
            color: #fff !important;
        }
        #tabs-bui42-tabpanel-0 {
            padding-top: 0 !important;
        }            

        /* Estilos a los selectores de familias y subfamilias*/
        span[data-baseweb="tag"] {
        font-size: 0.8em !important;
        margin: 1px !important;
        padding: 0px 2px !important;
        }
        div[data-baseweb="select"] {
            max-height: 120px;   /* altura máxima del contenedor */
            overflow-y: auto;    /* agrega scroll vertical si excede */
            font-size: 1rem;

        .stMultiSelect {
                background: linear-gradient(135deg, #ffffff 0%, #d1e8ff 100%);
                border: 2px solid #1e90ff;
                border-radius: 10px;
                padding: 6px;
                box-shadow: 0 2px 6px rgba(30, 144, 255, 0.25);
                transition: all 0.3s ease;
            }

</style>
"""

def custom_sidebar():
    return """
            <style>
            .sidebar-logo-box img {
            position: absolute;
                top: -4.4rem;
                max-width: 100%;
                border-radius: 8px;
                margin-bottom: 0.5rem;
                z-index: -1000;
            }

            .animated-title {
                font-weight: bold;
                color: #721c24;
                padding: 0.5rem 1rem;
            color: #1e3c72;
            background-color: #e9f5ff;
            border-left: 6px solid #2a5298;                            
                animation: pulse 1.5s infinite;
                border-radius: 5px;
                margin-bottom: .5rem;
            }

            .highlight-period {
                font-weight: bold;
                color: #856404;
                background: linear-gradient(90deg, #fff3cd, #ffeeba);
                padding: 0.5rem 1rem;
                border-left: 5px solid #ffc107;
                animation: blink 1.2s infinite;
                border-radius: 5px;
                margin-bottom: .5rem;
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.04); }
                100% { transform: scale(1); }
            }

            @keyframes blink {
                0% { opacity: 1; }
                50% { opacity: 0.6; }
                100% { opacity: 1; }
            }

            .stButton > button {
                background-color: #4368d6 !important;
                color: white !important;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                padding: 0.5rem 1rem;
            }

            .stButton > button:hover {
                background-color: #294ebc !important;
            }
                            
            /* Oculta el label específico apuntando al selector detallado */
            #root > div:nth-child(1) > div.withScreencast > div > div.stAppViewContainer.appview-container.st-emotion-cache-1yiq2ps.e4man110 > section > div.hideScrollbar.st-emotion-cache-jx6q2s.eu6y2f92 > div.st-emotion-cache-ja5xo9.eu6y2f91 > div > div > div:nth-child(3) > div > label {
                display: none !important;
            }

            </style>
            <div class="sidebar-logo-box">
                <img src="https://raw.githubusercontent.com/JulioLaz/proveedores_cucher/main/img/cucher_mercados.webp" alt="Cucher Mercados Logo">
            </div>
        """