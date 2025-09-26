# app/streamlit_app.py
import os
import sys
import traceback
import streamlit as st

# ensure project root in sys.path (helpful for imports)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Basic debug info shown immediately ---
st.set_page_config(page_title="Workflow Copilot (debug)", layout="wide")
st.title("Workflow Copilot — Debug Mode")

st.markdown("**Quick debug info — safe to ignore in normal runs**")
st.write("Working directory:", os.getcwd())
st.write("Project root (added to sys.path):", project_root)
st.write("sys.path (first 5):", sys.path[:5])

# show the files present (helps catch path problems)
try:
    st.write("Top-level files/folders:")
    st.write(os.listdir(project_root))
    st.write("app folder contents:", os.listdir(os.path.join(project_root, "app")))
    st.write("utils folder contents:", os.listdir(os.path.join(project_root, "utils")))
except Exception as e:
    st.warning(f"Could not list files: {e}")

# A small safe mock generator (local, offline)
def mock_generate(query, docs, industry):
    steps = "\n".join([f"{i+1}. {d}" for i, d in enumerate(docs)])
    return f"Workflow for {industry}:\nQuery: {query}\nSteps:\n{steps}\n\nHUMAN REVIEW REQUIRED."

# Lazy initialization function - heavy work goes here
@st.cache_resource
def init_services_safe():
    """
    This function should import heavy modules and build vector DB.
    It's wrapped in try/except so Streamlit won't die silently.
    """
    info = {"ok": False, "error": None}
    try:
        # Do heavy imports inside function so page renders first
        from app import rag
        from utils import safety
        # Build vectorstore (may download embeddings on first run)
        db = rag.build_vectorstore("data/protocols.json")
        retriever = rag.make_retriever(db, k=3)
        info.update({"ok": True, "rag": rag, "safety": safety, "db": db, "retriever": retriever})
    except Exception as e:
        tb = traceback.format_exc()
        print("Exception during init_services_safe:\n", tb)   # printed in terminal
        info["error"] = tb
    return info

# UI controls
st.sidebar.header("Controls")
if st.sidebar.button("Initialize services (loads embeddings/index)"):
    with st.spinner("Initializing services — may take 30–90s on first run..."):
        services = init_services_safe()
        if services.get("ok"):
            st.success("Services initialized successfully.")
        else:
            st.error("Initialization failed. See 'Init error' area below.")
            st.code(services.get("error") or "Unknown error")

# Input area
industry = st.selectbox("Industry context", ["general", "biotech", "materials", "environment", "finance"])
query = st.text_area("Describe the experiment / workflow you want", height=120)

# When user clicks generate:
if st.button("Generate workflow"):
    # If services available and OK, use them; otherwise use mock
    services = None
    try:
        services = init_services_safe()
    except Exception as e:
        print("init_services_safe call failed:", e)

    # PHI check (best-effort)
    phi_flag = False
    try:
        if services and services.get("ok"):
            safety = services["safety"]
            phi_flag = safety.contains_phi(query)
        else:
            # fallback simple check
            phi_flag = any(k in query.lower() for k in ["patient", "dob", "mrn", "ssn", "@"])
    except Exception as e:
        print("PHI detection error:", e)
        phi_flag = False

    if phi_flag:
        st.error("Input appears to contain PHI/PII. Please remove sensitive information.")
        # show de-identified example if available
        try:
            if services and services.get("ok"):
                st.code(services["safety"].deidentify_text(query))
            else:
                st.code("**De-identify manually** (mock): remove names, DOB, MRN, emails.")
        except Exception:
            st.code("**De-identify manually** (mock): remove names, DOB, MRN, emails.")
    else:
        # retrieve relevant docs
        try:
            if services and services.get("ok"):
                retriever = services["retriever"]
                docs = retriever.get_relevant_documents(query)
                docs_text = [d.page_content for d in docs]
                # try using rag openai helper if present; otherwise use rag.mock_generate if available
                try:
                    rag = services["rag"]
                    # prefer mock to avoid cloud calls in debug mode
                    generated = rag.mock_generate(query, docs, industry)
                except Exception as e:
                    print("rag usage error:", e)
                    generated = mock_generate(query, docs_text, industry)
            else:
                # no services: do a simple keyword retrieval from data/protocols.json
                import json
                with open(os.path.join(project_root, "data", "protocols.json")) as f:
                    docs_list = json.load(f)
                # naive match: any doc whose text contains any word from query
                qwords = [w.lower() for w in query.split() if len(w) > 3]
                matches = []
                for d in docs_list:
                    text = d.get("text","").lower()
                    if any(w in text for w in qwords):
                        matches.append(d.get("text"))
                if not matches:
                    matches = [d.get("text") for d in docs_list][:2]
                generated = mock_generate(query, matches, industry)
                docs_text = matches
        except Exception as e:
            tb = traceback.format_exc()
            print("Error during retrieval/generation:\n", tb)
            st.error("Generation failed; see terminal for full traceback.")
            st.code(tb)
            generated = mock_generate(query, [], industry)
            docs_text = []

        # show output
        st.markdown("### Generated workflow")
        st.code(generated)
        st.markdown("### Retrieved context (trace)")
        for i, d in enumerate(docs_text):
            st.write(f"**Source {i+1}:** {str(d)[:500]}{'...' if len(str(d))>500 else ''}")

# Show any cached init error for convenience
try:
    cached = init_services_safe()
    if cached and cached.get("error") and not cached.get("ok"):
        st.markdown("---")
        st.error("Init error (cached):")
        st.code(cached.get("error"))
except Exception:
    pass

st.markdown("---")
st.caption("Debug mode: initialize services manually to avoid blocking the UI on import. Contact dev for help.")
