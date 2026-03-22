import json
import streamlit as st
from streamlit_javascript import st_javascript


def get_dom_bboxes_js():
    js_code = '''
    (() => {
        const root = document.getElementById("reading-dom-text");
        if (!root) {
            return { ok: false, error: "reading-dom-text non trovato nel DOM" };
        }

        const rootRect = root.getBoundingClientRect();
        const stimulusId = root.dataset.stimulusId || null;
        const nodes = Array.from(root.querySelectorAll(".reading-word"));

        const items = nodes.map((el) => {
            const r = el.getBoundingClientRect();
            return {
                stimulus_id: stimulusId,
                token_id: el.dataset.tokenId || null,
                word_index: Number(el.dataset.wordIndex),
                line_index_declared: Number(el.dataset.lineIndexDeclared),
                token_type: el.dataset.tokenType || "word",
                word_text: (el.textContent || "").trim(),

                x: r.left,
                y: r.top,
                width: r.width,
                height: r.height,
                x_center: r.left + (r.width / 2),
                y_center: r.top + (r.height / 2),

                rel_x: r.left - rootRect.left,
                rel_y: r.top - rootRect.top,
                rel_x_center: (r.left - rootRect.left) + (r.width / 2),
                rel_y_center: (r.top - rootRect.top) + (r.height / 2),

                root_x: rootRect.left,
                root_y: rootRect.top,
                root_width: rootRect.width,
                root_height: rootRect.height
            };
        });

        return {
            ok: true,
            stimulus_id: stimulusId,
            bbox_items: items,
            timestamp: Date.now()
        };
    })()
    '''
    return st_javascript(js_code)


def ui_bbox_debug():
    st.markdown("### Debug Bounding Box DOM")

    if st.button("Calcola bounding box DOM"):
        data = get_dom_bboxes_js()

        if data and data.get("ok"):
            st.success(f"Ricevuti {len(data.get('bbox_items', []))} token")
            st.json(data)
            st.download_button(
                "Scarica JSON",
                data=json.dumps(data, ensure_ascii=False, indent=2),
                file_name="reading_dom_bbox.json",
                mime="application/json",
            )
        else:
            st.error(data.get("error", "Nessun dato ricevuto") if isinstance(data, dict) else "Nessun dato ricevuto")
