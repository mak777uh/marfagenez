"""Build a questionnaire for the owner: HTML, autosave, download, and a free-text field on every question.

Why a generator and not hand-written HTML: the owner asked, once, that **every** question carry a
"своими словами" field, and that questionnaires stay HTML. A rule that lives only in a chat message is
forgotten by the next agent; a generator makes it structural — there is no way to emit a question without
that field.

Spec (JSON):
    {"title": "...", "intro": "...", "out_name": "мои-ответы-3",
     "sections": [{"title": "...", "hint": "...",
                   "questions": [{"id": "q1", "text": "...", "why": "...",
                                  "type": "radio|checkbox|text",
                                  "options": [{"value": "a", "label": "...", "note": "..."}]}]}]}

Usage:
    python3 tools/ask_owner.py --spec tools/ask_specs/example.json --out QUESTIONNAIRE.html
"""

from __future__ import annotations

import html
import json
import pathlib
import sys

SPEC_DEFAULT = "tools/ask_specs/example.json"


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def render_question(q: dict, index: int) -> str:
    qid = esc(q["id"])
    kind = q.get("type", "radio")
    lines = [
        f'    <div class="card" data-q="{qid}">',
        f'      <p class="q">{index}. {esc(q["text"])}</p>',
    ]
    if q.get("why"):
        lines.append(f'      <p class="why">{esc(q["why"])}</p>')
    if kind in ("radio", "checkbox"):
        for opt in q.get("options", []):
            note = f'<small>{esc(opt["note"])}</small>' if opt.get("note") else ""
            lines.append(
                f'      <label class="opt"><input type="{kind}" name="{qid}" value="{esc(opt["value"])}">'
                f' <span>{esc(opt["label"])}{note}</span></label>'
            )
    # the field the owner asked for: always present, never optional by accident
    lines.append(
        f'      <textarea name="{qid}_free" rows="2" '
        f'placeholder="Своими словами — как вы это понимаете, что для вас важно"></textarea>'
    )
    lines.append("    </div>")
    return "\n".join(lines)


def render(spec: dict) -> str:
    title = esc(spec.get("title", "Опросник"))
    intro = esc(spec.get("intro", ""))
    out_name = esc(spec.get("out_name", "мои-ответы"))
    sections = []
    index = 0
    for section in spec.get("sections", []):
        body = [f'  <section>', f'    <h2>{esc(section["title"])}</h2>']
        if section.get("hint"):
            body.append(f'    <p class="hint">{esc(section["hint"])}</p>')
        for question in section.get("questions", []):
            index += 1
            body.append(render_question(question, index))
        body.append("  </section>")
        sections.append("\n".join(body))

    total = index
    titles = {
        q["id"]: q["text"]
        for section in spec.get("sections", [])
        for q in section.get("questions", [])
    }

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root{{--bg:#0f1115;--card:#171a21;--line:#262b36;--text:#e7e9ee;--muted:#9aa4b2;--accent:#4f8cff;--accent2:#39d98a;--info:#7c5cff}}
  @media (prefers-color-scheme: light){{:root{{--bg:#f5f6f8;--card:#fff;--line:#e2e5ea;--text:#16181d;--muted:#5d6673}}}}
  *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 -apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
  header{{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
  .wrap{{max-width:920px;margin:0 auto;padding:18px 20px}}
  h1{{font-size:22px;margin:0 0 6px}} .sub{{color:var(--muted);font-size:14px;margin:0}}
  .bar{{height:6px;background:var(--line);border-radius:99px;overflow:hidden;margin:14px 0 4px}}
  .bar>i{{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .25s}}
  .bar-label{{font-size:12px;color:var(--muted)}}
  section{{margin:26px 0}} h2{{font-size:17px;margin:0 0 4px}}
  .hint{{color:var(--muted);font-size:13.5px;margin:2px 0 12px}}
  .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 16px 10px;margin:12px 0}}
  .q{{font-weight:600;margin:0 0 4px}} .why{{color:var(--muted);font-size:13.5px;margin:0 0 10px}}
  label.opt{{display:flex;gap:10px;align-items:flex-start;padding:8px 10px;border-radius:10px;cursor:pointer}}
  label.opt:hover{{background:color-mix(in srgb,var(--accent) 9%,transparent)}}
  label.opt input{{margin-top:3px;accent-color:var(--accent);width:16px;height:16px}}
  .opt small{{display:block;color:var(--muted);font-size:12.5px}}
  textarea{{width:100%;background:transparent;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font:inherit;margin-top:8px;resize:vertical}}
  textarea:focus{{outline:2px solid color-mix(in srgb,var(--accent) 45%,transparent);border-color:var(--accent)}}
  .sticky-actions{{position:sticky;bottom:0;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:12px 0}}
  .actions{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
  button{{font:inherit;font-weight:600;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);padding:10px 16px;cursor:pointer}}
  button.primary{{background:var(--accent);border-color:var(--accent);color:#fff}} button.ghost{{background:transparent}}
  .saved{{font-size:13px;color:var(--accent2)}} .tiny{{font-size:12.5px;color:var(--muted)}}
  .answered{{border-color:color-mix(in srgb,var(--accent2) 55%,var(--line))}}
  code{{background:color-mix(in srgb,var(--line) 60%,transparent);padding:1px 5px;border-radius:5px;font-size:13px}}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>{title}</h1>
  <p class="sub">{intro}</p>
  <div class="bar"><i id="bar"></i></div>
  <div class="bar-label" id="barLabel">отвечено 0 из {total}</div>
</div></header>
<main class="wrap">
{chr(10).join(sections)}
  <div class="sticky-actions"><div class="wrap actions">
    <button class="primary" id="download">Скачать ответы</button>
    <button id="copy">Скопировать</button>
    <button class="ghost" id="reset">Очистить</button>
    <span class="saved" id="saved"></span>
  </div>
  <p class="tiny" style="margin:8px 0 0">Сохранится как <code>{out_name}.md</code>. Ответы хранятся в этом браузере.</p>
  </div>
</main>
<script>
(function(){{
  var KEY="ask-owner-"+"{out_name}"; var TOTAL={total}; var TITLES={json.dumps(titles, ensure_ascii=False)};
  function collect(){{
    var out={{}};
    document.querySelectorAll("input[type=radio]:checked").forEach(function(el){{out[el.name]=el.value;}});
    var checks={{}};
    document.querySelectorAll("input[type=checkbox]:checked").forEach(function(el){{(checks[el.name]=checks[el.name]||[]).push(el.value);}});
    Object.keys(checks).forEach(function(k){{out[k]=checks[k];}});
    document.querySelectorAll("textarea").forEach(function(el){{if(el.value.trim())out[el.name]=el.value.trim();}});
    return out;
  }}
  function answered(){{
    var n=0;
    document.querySelectorAll(".card").forEach(function(card){{
      var els=card.querySelectorAll("input, textarea");
      if(Array.prototype.some.call(els,function(el){{return el.checked || (el.value && el.value.trim());}}))n++;
    }});
    return n;
  }}
  function paint(){{
    var n=answered();
    document.getElementById("bar").style.width=Math.round(n/TOTAL*100)+"%";
    document.getElementById("barLabel").textContent="отвечено "+n+" из "+TOTAL;
    document.querySelectorAll(".card").forEach(function(card){{
      var els=card.querySelectorAll("input, textarea");
      var has=Array.prototype.some.call(els,function(el){{return el.checked || (el.value && el.value.trim());}});
      card.classList.toggle("answered",has);
    }});
  }}
  function save(){{try{{localStorage.setItem(KEY,JSON.stringify(collect()));}}catch(e){{}}
    var s=document.getElementById("saved"); s.textContent="сохранено "+new Date().toLocaleTimeString("ru-RU");
    setTimeout(function(){{s.textContent="";}},2500);}}
  function restore(){{
    var raw=null; try{{raw=localStorage.getItem(KEY);}}catch(e){{}} if(!raw)return;
    var data; try{{data=JSON.parse(raw);}}catch(e){{return;}}
    Object.keys(data).forEach(function(name){{
      var v=data[name];
      if(Array.isArray(v)){{v.forEach(function(x){{var el=document.querySelector('[name="'+name+'"][value="'+x+'"]');if(el)el.checked=true;}});}}
      else{{var radios=document.querySelectorAll('input[type=radio][name="'+name+'"]');
        if(radios.length){{radios.forEach(function(r){{r.checked=(r.value===v);}});}}
        else{{var el=document.querySelector('[name="'+name+'"]');if(el)el.value=v;}}}}
    }});
  }}
  function md(){{
    var d=collect(); var lines=["# {title}","","Дата: "+new Date().toLocaleString("ru-RU"),""];
    Object.keys(TITLES).forEach(function(id){{
      var v=d[id], free=d[id+"_free"];
      if(v===undefined && !free){{lines.push("**"+TITLES[id]+"** — _не ответил_");lines.push("");return;}}
      if(v!==undefined)lines.push("**"+TITLES[id]+"** — "+(Array.isArray(v)?v.join(", "):v));
      else lines.push("**"+TITLES[id]+"** — _только словами_");
      if(free)lines.push("  - своими словами: "+free);
      lines.push("");
    }});
    return lines.join("\\n");
  }}
  document.getElementById("download").addEventListener("click",function(){{
    var b=new Blob([md()],{{type:"text/markdown;charset=utf-8"}});var a=document.createElement("a");
    a.href=URL.createObjectURL(b);a.download="{out_name}.md";document.body.appendChild(a);a.click();a.remove();}});
  document.getElementById("copy").addEventListener("click",function(){{
    var t=md();
    if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(t).then(function(){{
      var s=document.getElementById("saved");s.textContent="скопировано";setTimeout(function(){{s.textContent="";}},2000);}});}}
    else{{var ta=document.createElement("textarea");ta.value=t;document.body.appendChild(ta);ta.select();document.execCommand("copy");ta.remove();}}
  }});
  document.getElementById("reset").addEventListener("click",function(){{
    if(!confirm("Очистить все ответы?"))return;
    try{{localStorage.removeItem(KEY);}}catch(e){{}}
    document.querySelectorAll("input, textarea").forEach(function(el){{if(el.type==="radio"||el.type==="checkbox")el.checked=false;else el.value="";}});
    paint();}});
  document.addEventListener("input",paint);
  document.addEventListener("change",function(){{save();paint();}});
  restore();paint();
}})();
</script>
</body>
</html>
"""


def main(argv: list[str]) -> int:
    spec_path = argv[argv.index("--spec") + 1] if "--spec" in argv else SPEC_DEFAULT
    out = argv[argv.index("--out") + 1] if "--out" in argv else "QUESTIONNAIRE.html"
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding="utf-8"))
    target = pathlib.Path(out)
    target.write_text(render(spec), encoding="utf-8")
    questions = sum(len(s.get("questions", [])) for s in spec.get("sections", []))
    print(f"{target}: {questions} вопросов, у каждого поле «своими словами»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
