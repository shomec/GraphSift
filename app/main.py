import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram

# Ensure parent directory is in sys.path for absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.generator import generate_dataset, generate_anomalies, gen_user_profile, gen_payment_charge, gen_inventory_item
from app.engine import SchemaAuditEngine, FEATURE_NAMES, extract_features

# Set page configuration with a premium dark theme
st.set_page_config(
    page_title="GraphSift | API Payload Audit Engine",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom premium CSS styles (Glassmorphism, clean dark backgrounds, glow borders, metrics styling)
st.markdown(
    """
    <style>
    /* Main Background & Fonts */
    .stApp {
        background-color: #0d0f14;
        color: #e2e8f0;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #141722;
        border-right: 1px solid #232936;
    }
    
    /* Titles and Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
        font-weight: 700 !important;
        letter-spacing: -0.025em;
    }
    
    .glow-header {
        background: linear-gradient(135deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        margin-bottom: 0.2rem;
        font-weight: 800;
        text-shadow: 0 0 40px rgba(129, 140, 248, 0.2);
    }
    
    .subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Custom Card Design */
    .glass-card {
        background: rgba(22, 28, 45, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        margin-bottom: 1.5rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Drift Alerts */
    .alert-container {
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1.5rem;
        border-left: 5px solid;
    }
    
    .alert-critical {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.3);
        border-left: 5px solid #ef4444;
    }
    
    .alert-warning {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        border-left: 5px solid #f59e0b;
    }
    
    .alert-normal {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-left: 5px solid #10b981;
    }
    
    /* Code highlight & tables */
    .stCodeBlock {
        border: 1px solid #232936 !important;
        border-radius: 8px !important;
    }
    
    /* Buttons */
    div.stButton > button {
        background: linear-gradient(135deg, #4f46e5, #3b82f6);
        border: none;
        color: white;
        padding: 0.5rem 2rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }
    
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(79, 70, 229, 0.5);
        background: linear-gradient(135deg, #6366f1, #3b82f6);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- SIDEBAR: DATASET PARAMETERS ---
st.sidebar.markdown("### 🕸️ Model Parameters")

clean_count = st.sidebar.slider("Clean Payload Samples", min_value=30, max_value=250, value=120, step=10)
noise_count = st.sidebar.slider("Noisy Background Samples", min_value=0, max_value=100, value=30, step=5)

st.sidebar.markdown("### 🛠️ Clustering Settings")
linkage_method = st.sidebar.selectbox("Linkage Method", ["ward", "complete", "average"], index=0)

# Ward linkage only supports Euclidean distance
distance_metrics = ["euclidean"] if linkage_method == "ward" else ["euclidean", "cosine", "cityblock"]
distance_metric = st.sidebar.selectbox("Distance Metric", distance_metrics, index=0)

n_clusters = st.sidebar.slider("Target Endpoint Clusters (k)", min_value=2, max_value=6, value=3)

# Data Quality sandbox mode toggle
st.sidebar.markdown("### 🧠 Unsupervised Learning Mode")
data_quality_mode = st.sidebar.radio(
    "Data Quality Filter:",
    ["Clean Training Data (Best Practice)", "Raw / Noisy Training Data (No Filters)"],
    index=0
)

# Header Section
st.markdown("<div class='glow-header'>GraphSift</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>API Payload Structure & Dependency Audit Engine for Resilient Microservices</div>", unsafe_allow_html=True)

# Overview text demonstrating unsupervised clustering purpose
st.markdown(
    """
    <div class='glass-card'>
        <h4>🔬 The Unsupervised Learning & Data Quality Mandate</h4>
        <p>
            In production systems, microservices continuously exchange JSON payloads. Changes in payload structure (new schemas, redundant keys, or type shifts) 
            can degrade database performance, crash pipelines, and open security vulnerability surfaces. 
        </p>
        <p>
            <b>GraphSift</b> demonstrates how <b>unsupervised clustering</b> groups structures into natural endpoint schemas, and how 
            an <b>Isolation Forest</b> detects structural drift. It also showcases a fundamental rule of machine learning: 
            <b>Data Quality is Everything.</b> Training models on unfiltered, noisy data compromises clustering boundaries, yielding 
            inaccurate schemas and high false alarm rates.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- GENERATE DATASET & TRAIN MODEL ---
@st.cache_data(show_spinner=False)
def get_cached_dataset(n_clean, n_noise):
    return generate_dataset(n_clean=n_clean, n_noise=n_noise)

# If Clean Training Mode is selected, we filter out noise from the training set.
# This proves the exact point: removing noise is critical for high quality unsupervised models.
raw_dataset = get_cached_dataset(clean_count, noise_count)

if data_quality_mode == "Clean Training Data (Best Practice)":
    # Filter the dataset to include ONLY clean endpoints (simulate data clearing pipeline)
    training_dataset = [item for item in raw_dataset if item["label"] == "clean"]
    is_data_clean = True
else:
    # Train on everything including crawling scrapers, stack trace noise, and error logs (raw ingestion)
    training_dataset = raw_dataset
    is_data_clean = False

# Fit clustering and anomaly engine
engine = SchemaAuditEngine(linkage_method=linkage_method, distance_metric=distance_metric)
engine.fit_and_cluster(training_dataset, n_clusters=n_clusters)
df_summary = engine.get_summary_df()

# Compute evaluation metrics to display to the user
cophenetic_score = engine.cophenetic_corr
noise_in_training = len([x for x in training_dataset if x["label"] == "noise"])
noisy_ratio = noise_in_training / len(training_dataset) * 100

# --- METRIC CARDS ROW ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">Training Set Size</div>
            <div class="metric-value" style="color: #6366f1;">{len(training_dataset)}</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">API structures ingesting</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    color = "#ef4444" if noisy_ratio > 0 else "#10b981"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">Noise Contamination</div>
            <div class="metric-value" style="color: {color};">{noisy_ratio:.1f}%</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">{noise_in_training} noisy payloads in training</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col3:
    # Linkage correlation quality indicator
    coph_color = "#10b981" if cophenetic_score > 0.8 else "#f59e0b" if cophenetic_score > 0.6 else "#ef4444"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">Cophenetic Coefficient</div>
            <div class="metric-value" style="color: {coph_color};">{cophenetic_score:.3f}</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">Clustering hierarchy reliability</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col4:
    # Model Status
    status_text = "OPTIMIZED BOUNDARY" if is_data_clean else "COMPROMISED BOUNDARY"
    status_color = "#10b981" if is_data_clean else "#f59e0b"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">Model Protection Status</div>
            <div class="metric-value" style="color: {status_color}; font-size: 1.45rem; padding: 0.35rem 0;">{status_text}</div>
            <div style="font-size: 0.8rem; color: #94a3b8;">Data Sifting Pipeline is {"Active" if is_data_clean else "Disabled"}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# --- VISUALIZATIONS SECTION ---
st.markdown("### 📊 Clustering Architecture & Dimensional Spaces")

vis_col1, vis_col2 = st.columns([1, 1])

with vis_col1:
    st.markdown("#### 🪵 Hierarchical Dendrogram (Endpoint Groupings)")
    # Generate hierarchical dendrogram using matplotlib
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="#141722")
    ax.set_facecolor("#141722")
    
    # We assign label identifiers representing the microservice endpoints or noise
    dendrogram_labels = []
    for i in range(len(training_dataset)):
        endpoint_name = training_dataset[i]["endpoint"]
        label_class = training_dataset[i]["label"]
        dendrogram_labels.append(f"{endpoint_name} ({label_class[0].upper()})")
        
    dendrogram(
        engine.linkage_matrix,
        labels=dendrogram_labels,
        ax=ax,
        color_threshold=np.percentile(engine.linkage_matrix[:, 2], 70),
        above_threshold_color="#475569",
        leaf_rotation=90,
        leaf_font_size=6
    )
    
    # Format labels and styles to align with dark UI
    ax.spines['bottom'].set_color('#232936')
    ax.spines['top'].set_color('#232936')
    ax.spines['left'].set_color('#232936')
    ax.spines['right'].set_color('#232936')
    ax.tick_params(axis='x', colors='#94a3b8')
    ax.tick_params(axis='y', colors='#94a3b8')
    ax.set_title("Agglomerative Dendrogram showing API Shape Clusters", color="#f8fafc", fontsize=10)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

with vis_col2:
    st.markdown("#### 🌌 2D Principal Component Projection (PCA)")
    # Setup interactive Plotly scatter plot for PCA projection
    fig_pca = px.scatter(
        df_summary,
        x="pca_x",
        y="pca_y",
        color="cluster",
        symbol="endpoint",
        hover_data=["total_keys", "max_depth", "string_ratio", "numeric_ratio", "avg_string_length", "label"],
        title="Ingested payload shapes projected on 2D PCA Space",
        color_discrete_sequence=px.colors.qualitative.G10
    )
    
    # Custom plotly layout
    fig_pca.update_layout(
        plot_bgcolor="#141722",
        paper_bgcolor="#0d0f14",
        font_color="#94a3b8",
        xaxis=dict(showgrid=True, gridcolor="#232936", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#232936", zeroline=False),
        legend_title_text="Clustered Schemas",
        margin=dict(l=20, r=20, t=40, b=20),
        height=380
    )
    st.plotly_chart(fig_pca, use_container_width=True)

# --- DATA QUALITY SANDBOX COMPARISON ---
if not is_data_clean:
    st.markdown(
        """
        <div class="alert-container alert-warning">
            ⚠️ <b>CRITICAL WARNING: Training with Noise Contaminants!</b><br/>
            Notice that the clusters in the PCA diagram are overlapping, and the dendrogram is messy. 
            Because we are training the unsupervised model on web crawler logs, heartbeat ticks, and stack traces, the 
            system boundary is loose. Hackers or bloated schema drift will bypass this boundary, leading to security 
            breaches and service crashes. <b>Toggle 'Clean Training Data' in the sidebar to activate the sifting filter!</b>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="alert-container alert-normal">
            ✅ <b>Sifting Filter Active: High Quality Data Training!</b><br/>
            Unsupervised learning successfully grouped payloads into perfect microservice schemas. Notice the high Cophenetic Coefficient 
            (closer to 1.0 indicates stable clusters). Anomaly thresholds are tight and precise.
        </div>
        """,
        unsafe_allow_html=True
    )

# --- INGESTION & AUDIT SANDBOX ---
st.markdown("---")
st.markdown("### 🔍 Real-Time Ingestion Sandbox & Guardrail Audit")

sandbox_col1, sandbox_col2 = st.columns([1, 1])

# Preset payloads dictionary
preset_payloads = {
    "Happy Path: User Profile": gen_user_profile(),
    "Happy Path: Payment Charge": gen_payment_charge(),
    "Happy Path: Inventory Item": gen_inventory_item(),
    "Anomaly: Schema Bloat (Payment)": generate_anomalies()[1]["payload"],
    "Anomaly: Data Type Drift (User Profile)": generate_anomalies()[2]["payload"],
    "Anomaly: Deep Nesting DOS (15 Levels deep)": generate_anomalies()[4]["payload"],
    "Anomaly: Buffer Overflow (10KB base64/payload strings)": generate_anomalies()[5]["payload"],
}

with sandbox_col1:
    st.markdown("#### Input Ingested JSON Payload")
    
    preset_choice = st.selectbox(
        "Load Preset Payload Template:",
        ["Select a payload preset...", *preset_payloads.keys()]
    )
    
    initial_text = ""
    if preset_choice != "Select a payload preset...":
        initial_text = json.dumps(preset_payloads[preset_choice], indent=2)
        
    payload_input = st.text_area(
        "Raw JSON Ingestion Stream",
        value=initial_text,
        height=320,
        placeholder="Paste JSON API payload here..."
    )
    
    audit_triggered = st.button("Run Schema Audit Engine")

with sandbox_col2:
    st.markdown("#### Audit Outcome & Engineering Alert")
    
    if audit_triggered and payload_input.strip():
        try:
            parsed_payload = json.loads(payload_input)
            
            # Run drift audit
            audit_result = engine.detect_drift(parsed_payload)
            
            # Anomaly status alert
            if audit_result["anomaly_level"] == "CRITICAL":
                st.markdown(
                    f"""
                    <div class="alert-container alert-critical">
                        <h3>🚨 CRITICAL STRUCTURAL DRIFT DETECTED</h3>
                        <p><b>Decision:</b> TRAFFIC BLOCKED & ALIGNED FOR ROLLBACK</p>
                        <p><b>Anomaly Score:</b> {audit_result['score']:.4f} (Under boundary)</p>
                        <p><b>Centroid Distance:</b> {audit_result['distance_to_closest_centroid']:.2f} (Max threshold: {audit_result['distance_threshold']:.2f})</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif audit_result["anomaly_level"] == "WARNING":
                st.markdown(
                    f"""
                    <div class="alert-container alert-warning">
                        <h3>⚠️ MINOR STRUCTURAL DRIFT / WARN</h3>
                        <p><b>Decision:</b> AUDIT WARNING LOGGED (Payload structure modified)</p>
                        <p><b>Anomaly Score:</b> {audit_result['score']:.4f}</p>
                        <p><b>Centroid Distance:</b> {audit_result['distance_to_closest_centroid']:.2f} (Max threshold: {audit_result['distance_threshold']:.2f})</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div class="alert-container alert-normal">
                        <h3>✅ SCHEMA VERIFIED</h3>
                        <p><b>Decision:</b> INGESTION ALLOWED</p>
                        <p><b>Centroid Distance:</b> {audit_result['distance_to_closest_centroid']:.2f} (Max threshold: {audit_result['distance_threshold']:.2f})</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            # Plot new payload dynamically in the PCA projection
            pca_coords = audit_result["pca_coords"]
            
            fig_pca_update = go.Figure()
            
            # Plot training data
            for cluster_name in df_summary["cluster"].unique():
                c_df = df_summary[df_summary["cluster"] == cluster_name]
                fig_pca_update.add_trace(go.Scatter(
                    x=c_df["pca_x"],
                    y=c_df["pca_y"],
                    mode="markers",
                    name=cluster_name,
                    marker=dict(size=8, opacity=0.7),
                    hovertemplate="Cluster: " + cluster_name + "<br>Keys: %{customdata[0]}<br>Depth: %{customdata[1]}",
                    customdata=c_df[["total_keys", "max_depth"]].values
                ))
                
            # Plot new point
            color_new = "#ef4444" if audit_result["is_drift"] else "#10b981"
            symbol_new = "x" if audit_result["is_drift"] else "circle-dot"
            fig_pca_update.add_trace(go.Scatter(
                x=[pca_coords[0]],
                y=[pca_coords[1]],
                mode="markers",
                name="Ingested Payload",
                marker=dict(size=18, color=color_new, symbol=symbol_new, line=dict(width=3, color='#ffffff')),
                hovertemplate="NEW PAYLOAD<br>PCA X: %{x}<br>PCA Y: %{y}"
            ))
            
            fig_pca_update.update_layout(
                plot_bgcolor="#141722",
                paper_bgcolor="#0d0f14",
                font_color="#94a3b8",
                xaxis=dict(showgrid=True, gridcolor="#232936", zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="#232936", zeroline=False),
                legend_title_text="Clustered Schemas",
                margin=dict(l=10, r=10, t=10, b=10),
                height=280
            )
            
            st.plotly_chart(fig_pca_update, use_container_width=True)
            
            # Show feature differences in a table
            new_features = audit_result["features"]
            
            # Compute average features of the training set for reference
            avg_features = df_summary[FEATURE_NAMES].mean().tolist()
            
            comparison_data = {
                "Feature Metric": FEATURE_NAMES,
                "Ingested Value": [f"{v:.4f}" if isinstance(v, float) else str(v) for v in new_features],
                "Baseline Average": [f"{v:.4f}" for v in avg_features]
            }
            
            st.markdown("##### Feature Metric Comparison Breakdown:")
            st.table(pd.DataFrame(comparison_data))
            
        except json.JSONDecodeError:
            st.error("❌ Malformed input: The payload could not be parsed as valid JSON.")
        except Exception as e:
            st.error(f"❌ Verification Error: {str(e)}")
    else:
        st.info("💡 Paste a JSON payload or select a preset and trigger 'Run Schema Audit Engine' to execute unsupervised drift security guards.")
