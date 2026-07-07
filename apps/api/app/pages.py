"""Minimal server-rendered pages in the console aesthetic."""


def console_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — MO Academy</title>
<style>
  body {{ background:#0B0F0D; color:#D8D4C8; font-family:'IBM Plex Mono',Consolas,Menlo,monospace;
         display:grid; place-items:center; min-height:100vh; margin:0; padding:1rem; }}
  main {{ max-width:36rem; border:1px solid #8A6A1F; padding:2rem; background:#101612; }}
  h1 {{ color:#FFB000; font-size:1.3rem; }}
  a {{ color:#FFB000; }}
  a:focus-visible {{ outline:2px solid #FFB000; outline-offset:2px; }}
</style></head>
<body><main><h1>{title}</h1><p>{body}</p>
<p><a href="/">&larr; back to MO Academy</a></p></main></body></html>"""
