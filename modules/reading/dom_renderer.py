import html
import json
import re
from typing import List, Dict, Any


WORD_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize_text(text: str) -> List[Dict[str, Any]]:
    """
    Divide il testo in token semplici mantenendo:
    - parole
    - punteggiatura
    - ritorni a capo logici

    Output:
    [
        {
            "token_id": "tok_0",
            "word_index": 0,
            "text": "Ciao",
            "type": "word"
        },
        ...
    ]
    """
    tokens: List[Dict[str, Any]] = []
    word_index = 0

    lines = text.splitlines()

    for line_idx, line in enumerate(lines):
        parts = WORD_RE.findall(line)

        for part in parts:
            token_type = "word" if re.match(r"\w+", part, re.UNICODE) else "punct"
            tokens.append(
                {
                    "token_id": f"tok_{word_index}",
                    "word_index": word_index,
                    "line_index_declared": line_idx,
                    "text": part,
                    "type": token_type,
                }
            )
            word_index += 1

        if line_idx < len(lines) - 1:
            tokens.append(
                {
                    "token_id": f"br_{line_idx}",
                    "word_index": None,
                    "line_index_declared": line_idx,
                    "text": "\n",
                    "type": "linebreak",
                }
            )

    return tokens


def build_reading_html(
    text: str,
    stimulus_id: str,
    font_size_px: int = 30,
    line_height: float = 1.8,
    letter_spacing_px: float = 0.3,
    container_width: str = "100%",
    text_align: str = "left",
) -> str:
    """
    Costruisce HTML con ogni parola/punteggiatura in uno span separato.
    Il browser potrà poi misurare i bounding box reali.
    """
    tokens = tokenize_text(text)

    tokens_json = json.dumps(tokens, ensure_ascii=False)

    html_parts = [
        f"""
        <style>
        .reading-dom-root {{
            width: {container_width};
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #d9e2d9;
            border-radius: 12px;
            padding: 28px;
            box-sizing: border-box;
        }}

        .reading-dom-text {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: {font_size_px}px;
            line-height: {line_height};
            letter-spacing: {letter_spacing_px}px;
            color: #111;
            text-align: {text_align};
            white-space: normal;
            word-wrap: break-word;
        }}

        .reading-word {{
            display: inline-block;
            position: relative;
            margin-right: 0.22em;
            margin-bottom: 0.05em;
            border-radius: 4px;
            padding: 0 1px;
        }}

        .reading-word.word-seen {{
            background: rgba(80, 140, 255, 0.22);
        }}

        .reading-word.word-high-dwell {{
            background: rgba(255, 210, 70, 0.35);
        }}

        .reading-word.word-revisited {{
            background: rgba(255, 90, 90, 0.30);
        }}

        .reading-word.word-skipped {{
            background: rgba(180, 180, 180, 0.22);
        }}

        .reading-linebreak {{
            display: block;
            height: 0;
            width: 100%;
        }}
        </style>
        """
    ]

    html_parts.append(f'<div class="reading-dom-root" id="reading-dom-root-{html.escape(stimulus_id)}">')
    html_parts.append(
        f'<div class="reading-dom-text" id="reading-dom-text" data-stimulus-id="{html.escape(stimulus_id)}">'
    )

    for token in tokens:
        ttype = token["type"]

        if ttype == "linebreak":
            html_parts.append('<span class="reading-linebreak"></span>')
            continue

        token_id = html.escape(str(token["token_id"]))
        token_text = html.escape(str(token["text"]))
        token_type = html.escape(str(token["type"]))
        word_index = html.escape(str(token["word_index"]))
        line_idx_declared = html.escape(str(token["line_index_declared"]))

        html_parts.append(
            f"""
            <span
                class="reading-word"
                data-token-id="{token_id}"
                data-word-index="{word_index}"
                data-line-index-declared="{line_idx_declared}"
                data-token-type="{token_type}"
            >{token_text}</span>
            """
        )

    html_parts.append("</div></div>")

    html_parts.append(
        f"""
        <script>
        window.READING_TOKENS = {tokens_json};
        window.READING_STIMULUS_ID = {json.dumps(stimulus_id, ensure_ascii=False)};
        </script>
        """
    )

    return "\n".join(html_parts)
