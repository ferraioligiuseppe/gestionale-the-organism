def org_header(title, subtitle=""):
    st.markdown(
        f"""
        <div class="org-hero">
            <h2 style="margin-bottom:4px">{title}</h2>
            <p style="opacity:0.9">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
