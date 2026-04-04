from html.parser import HTMLParser

class DivParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.div_stack = []
        self.lines = open("app/templates/admin/deudores.html", "r").readlines()

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            line = self.getpos()[0]
            self.div_stack.append((line, self.lines[line-1].strip()))

    def handle_endtag(self, tag):
        if tag == "div":
            if self.div_stack:
                self.div_stack.pop()
            else:
                print(f"Unmatched </div> at line {self.getpos()[0]}")

parser = DivParser()
with open("app/templates/admin/deudores.html", "r") as f:
    parser.feed(f.read())
for line, content in parser.div_stack:
    print(f"Unclosed <div ...> from line {line}: {content}")
