"""Bosmaxona shabloni (PDF -> SVG, pdftocairo) bilan ishlash: elementlar o'rnini topish,
kerakli zonalardagi eski dizaynni olib tashlash va yangi dizaynni joylash."""
import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
NS = "{%s}" % SVG_NS

_NUM = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def parse_matrix(s):
    if not s:
        return (1, 0, 0, 1, 0, 0)
    m = re.match(r"\s*matrix\(([^)]*)\)", s)
    assert m, s
    return tuple(float(v) for v in re.split(r"[\s,]+", m.group(1).strip()))


def mul(m1, m2):
    """m1 * m2 (avval m2, keyin m1)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2, a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def apply(m, x, y):
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


class Template:
    def __init__(self, path):
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.defs = self.root.find(NS + "defs")
        if self.defs is None:
            self.defs = ET.Element(NS + "defs")
            self.root.insert(0, self.defs)
        self.sources = {}
        for e in self.root.iter():
            if e.get("id"):
                self.sources[e.get("id")] = e
        self._fix_scale()

    def _fix_scale(self):
        """pdftocairo -svg sahifani ~0.998 masshtabda yozadi (PDF dagi asl koordinatalardan farq qiladi).
        Asl PDF bilan millimetrma-millimetr mos bo'lishi uchun hamma narsani teskari matritsali
        guruhga o'raymiz. Ichki koordinatalar (k, ty) shu guruh ichida o'zgarmaydi."""
        import collections
        cnt = collections.Counter()
        for e in self.root.iter():
            m = parse_matrix(e.get("transform")) if e.get("transform") else None
            if m and e.get("stroke") not in (None, "none") and abs(m[1]) < 1e-9 and abs(m[2]) < 1e-9 \
                    and m[3] < 0 and abs(m[0] + m[3]) < 1e-9:
                cnt[(m[0], m[4], m[5])] += 1
        self.k, self.ex, self.ty = cnt.most_common(1)[0][0] if cnt else (1.0, 0.0, None)
        self.page_h = float(re.match(r"[\d.]+", self.root.get("height")).group(0))
        if self.ty is None:
            self.ty = self.page_h
        k = self.k
        self.fix = (1 / k, 0, 0, 1 / k, -self.ex / k, self.page_h - self.ty / k)
        self.layer = ET.Element(NS + "g", {"id": "SHABLON",
                                           "transform": "matrix(%s)" % ", ".join(f"{v:.8f}" for v in self.fix)})
        for e in [c for c in list(self.root) if c.tag != NS + "defs"]:
            self.root.remove(e)
            self.layer.append(e)
        self.root.append(self.layer)

    def bbox(self, e, m=(1, 0, 0, 1, 0, 0)):
        m = mul(m, parse_matrix(e.get("transform")))
        tag = e.tag.replace(NS, "")
        pts = []
        if tag == "path":
            nums = [float(v) for v in _NUM.findall(e.get("d", ""))]
            pts = [apply(m, nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        elif tag == "use":
            href = e.get("{%s}href" % XLINK_NS, "").lstrip("#")
            src = self.sources.get(href)
            if src is not None:
                w, h = float(src.get("width", 0)), float(src.get("height", 0))
                pts = [apply(m, x, y) for x, y in [(0, 0), (w, 0), (0, h), (w, h)]]
        elif tag == "image":
            x, y = float(e.get("x", 0)), float(e.get("y", 0))
            w, h = float(e.get("width", 0)), float(e.get("height", 0))
            pts = [apply(m, px, py) for px, py in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]]
        boxes = [b for b in (self.bbox(c, m) for c in e) if b]
        if pts:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
        if not boxes:
            return None
        return (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))

    def drawables(self):
        return list(self.layer)

    @staticmethod
    def is_stroke_only(e):
        """Faqat chiziqdan iborat element (yoki faqat chiziqlardan iborat guruh)."""
        leaves = [x for x in e.iter() if x.tag.replace(NS, "") in ("path", "use", "image", "rect")]
        return bool(leaves) and all(x.get("stroke") not in (None, "none") and x.get("fill") == "none"
                                    for x in leaves)

    def drop_in(self, rects, keep=lambda e, b: False):
        """rects (sahifa koordinatalari, x0,y0,x1,y1) ichida markazi bo'lgan to'ldirilgan
        elementlarni o'chiradi. Chiziqlar (kesish/bukish, qizil zonalar) saqlanadi."""
        dropped = 0
        for e in self.drawables():
            if self.is_stroke_only(e):
                continue
            b = self.bbox(e)
            if not b:
                continue
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rects) and not keep(e, b):
                stroked = [x for x in e.iter() if x.get("stroke") not in (None, "none")]
                if stroked:
                    # kesish chizig'i va eski fon bitta obyektda: chiziqni qoldirib, fonni olib tashlaymiz
                    for x in e.iter():
                        if x.get("stroke") in (None, "none") and x.tag.replace(NS, "") == "path":
                            x.set("fill", "none")
                            x.set("stroke", "none")
                        elif x.get("stroke") not in (None, "none"):
                            x.set("fill", "none")
                    self.stripped = getattr(self, "stripped", 0) + 1
                    continue
                self.layer.remove(e)
                dropped += 1
        return dropped

    def add_defs(self, defs_xml):
        if not defs_xml:
            return
        frag = ET.fromstring(f'<defs xmlns="{SVG_NS}">{"".join(defs_xml)}</defs>')
        for c in list(frag):
            self.defs.append(c)

    def insert_art(self, svg_body, index=None):
        """Yangi dizayn bo'lagini qo'shadi (standart: eng pastki qatlam, defs dan keyin)."""
        g = ET.fromstring(f'<g xmlns="{SVG_NS}">{svg_body}</g>')
        self.layer.insert(index or 0, g)
        return g

    def append_art(self, svg_body):
        g = ET.fromstring(f'<g xmlns="{SVG_NS}">{svg_body}</g>')
        self.layer.append(g)
        return g

    def move_strokes_to_top(self):
        """Kesish/bukish chiziqlari va qizil zonalar dizayn ustida tursin."""
        for e in self.drawables():
            if self.is_stroke_only(e):
                self.layer.remove(e)
                self.layer.append(e)

    def write(self, path):
        # pdftocairo o'lchamni birliksiz (pt) yozadi; aniq o'lcham uchun "pt" qo'shamiz
        for att in ("width", "height"):
            v = self.root.get(att)
            if v and re.fullmatch(r"[\d.]+", v):
                self.root.set(att, v + "pt")
        self.tree.write(path, encoding="utf-8", xml_declaration=True)
