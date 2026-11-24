import importlib.util, re, html
spec = importlib.util.spec_from_file_location("e", "/root/marfagenez/scratch/_dip53_epmc.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
t = re.sub(r"<[^>]+>", " ", e.fulltext("PMC13319206"))
t = html.unescape(re.sub(r"\s+", " ", t))
for key in ["We obtained", "Péclet number of", "Pe ="]:
    i = t.find(key)
    if i >= 0:
        print(key, "=>", t[i:i+700], "\n")
