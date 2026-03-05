from __future__ import annotations
from pathlib import Path
import streamlit as st

def inject_ui(css_path: str = "assets/ui.css") -> None:
    """Inject global CSS once per session."""
    if st.session_state.get("_to_ui_injected"):
        return
    p = Path(css_path)
    if p.exists():
        st.markdown(f"<style>{p.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    st.session_state["_to_ui_injected"] = True

def topbar(title: str, subtitle: str = "", right: str = "") -> None:
    st.markdown(
        f"""
        <div class="to-topbar">
          <div>
            <div class="title">{title}</div>
            {f'<div class="sub">{subtitle}</div>' if subtitle else ''}
          </div>
          {f'<div class="sub">{right}</div>' if right else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )

def card_open(title: str, subtitle: str = "", icon: str = "👁️") -> None:
    st.markdown(
        f"""
        <div class="to-card">
          <div class="title">{icon} {title}</div>
          {f'<div class="sub">{subtitle}</div>' if subtitle else ''}
          <div class="to-divider"></div>
        """,
        unsafe_allow_html=True,
    )

def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)

def badge(text: str) -> None:
    st.markdown(
        f"""<span class="to-badge"><span class="dot"></span>{text}</span>""",
        unsafe_allow_html=True,
    )

def callout(text: str, variant: str = "default") -> None:
    variant_class = ""
    if variant in ("warn", "ok"):
        variant_class = f" {variant}"
    st.markdown(
        f"""<div class="to-callout{variant_class}">{text}</div>""",
        unsafe_allow_html=True,
    )

def cta_button(label: str, key: str | None = None, use_container_width: bool = False) -> bool:
    """Primary button styled with CSS wrapper."""
    st.markdown('<div class="to-cta">', unsafe_allow_html=True)
    clicked = st.button(label, key=key, use_container_width=use_container_width)
    st.markdown("</div>", unsafe_allow_html=True)
    return clicked
