#!/usr/bin/env python3
"""pptx-finalize: PPTX 폰트 임베드 → PDF 변환 → NFC 파일명 정규화.

워크플로우:
  1. pptx가 참조하는 typeface 자동 감지
  2. 로컬에 TTF로 설치된 폰트를 OOXML 규약대로 임베드 (Regular/Bold, 비파괴 _embedded.pptx)
  3. 임베드본을 LibreOffice headless로 PDF 변환 (로컬 폰트가 PDF에 박힘)
  4. 출력 파일명을 NFC로 정규화 (macOS NFD 한글명 문제 해결)
  5. 검증: zip 무결성 + pdffonts 임베드 확인

사용:
  python3 finalize.py INPUT.pptx [--out-dir DIR] [--soffice PATH] [--no-pdf] [--no-embed]

의존성: LibreOffice(soffice), fontconfig(fc-list). 검증용(선택): poppler(pdffonts).
"""
import argparse, os, re, shutil, subprocess, sys, unicodedata, zipfile

FONT_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"
# 임베드 불필요한 범용 시스템 폰트(라틴) — 본문 한글 폰트만 임베드, 잡음 typeface 제외
SKIP_FAMILIES = {"arial", "times new roman", "calibri", "cambria", "verdana",
                 "tahoma", "courier new", "segoe ui", "맑은 고딕", "malgun gothic"}

def log(msg): print(msg, flush=True)

def find_soffice(override=None):
    if override and os.path.exists(override):
        return override
    cands = ["/Applications/LibreOffice.app/Contents/MacOS/soffice",
             shutil.which("soffice"), shutil.which("libreoffice")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    return None

def scan_typefaces(pptx_path):
    """pptx 내부 모든 part에서 typeface="..." 참조를 카운트."""
    counts = {}
    with zipfile.ZipFile(pptx_path) as z:
        for n in z.namelist():
            if not n.endswith(".xml"):
                continue
            try:
                txt = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            for tf in re.findall(r'typeface="([^"]+)"', txt):
                if tf.strip():
                    counts[tf] = counts.get(tf, 0) + 1
    return counts

def build_font_index():
    """fc-list로 설치 폰트 인덱스: {family_lower: {'regular': path, 'bold': path}}.
    fontconfig 숫자 weight/slant로 정확히 분류. .ttf를 .otf보다 우선."""
    # fontconfig weight: regular=80, book=75 / bold=200. slant: roman=0.
    try:
        out = subprocess.check_output(
            ["fc-list", "--format=%{family}\t%{weight}\t%{slant}\t%{file}\n"],
            text=True, stderr=subprocess.DEVNULL)
    except Exception as e:
        log(f"  ! fc-list 실패: {e}")
        return {}
    idx = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        families, weight, slant, path = parts
        try:
            w, s = int(weight), int(slant)
        except ValueError:
            continue
        if s != 0:            # roman만 (italic/oblique 제외)
            continue
        if w in (75, 80):
            slot = "regular"
        elif w == 200:
            slot = "bold"
        else:                 # thin/light/medium/semibold/extrabold/black 등 제외
            continue
        ext = os.path.splitext(path)[1].lower()
        for fam in families.split(","):
            key = fam.strip().lower()
            if not key:
                continue
            entry = idx.setdefault(key, {})
            cur = entry.get(slot)
            if cur is None or (ext == ".ttf" and os.path.splitext(cur)[1].lower() != ".ttf"):
                entry[slot] = path
    return idx

def resolve_fonts(typefaces, font_idx):
    """참조된 typeface 중 로컬 설치된 것 → 임베드 대상. 반환: (embed_list, skipped, missing)."""
    embed, skipped, missing = [], [], []
    for tf in typefaces:
        if tf.startswith("+"):   # 테마 토큰(+mj-lt, +mn-ea 등) — 실제 폰트 아님
            continue
        key = tf.strip().lower()
        if key in SKIP_FAMILIES:
            skipped.append(tf); continue
        entry = font_idx.get(key)
        if not entry or "regular" not in entry:
            missing.append(tf); continue
        embed.append((tf, entry["regular"], entry.get("bold")))
    return embed, skipped, missing

def patch_presentation(xml, font_specs):
    """font_specs: [(typeface, reg_rid, bold_rid_or_None), ...]"""
    if "embedTrueTypeFonts" in xml:
        raise RuntimeError("이미 폰트가 임베드된 pptx입니다 (embedTrueTypeFonts 존재)")
    xml = xml.replace("<p:presentation ", '<p:presentation embedTrueTypeFonts="1" ', 1)
    fonts_xml = ""
    for tf, reg_rid, bold_rid in font_specs:
        slots = f'<p:regular r:id="{reg_rid}"/>'
        if bold_rid:
            slots += f'<p:bold r:id="{bold_rid}"/>'
        fonts_xml += f'<p:embeddedFont><p:font typeface="{tf}"/>{slots}</p:embeddedFont>'
    lst = f"<p:embeddedFontLst>{fonts_xml}</p:embeddedFontLst>"
    m = re.search(r'<p:notesSz[^>]*/>', xml)
    if not m:
        raise RuntimeError("notesSz를 찾지 못함 — presentation.xml 구조 이상")
    return xml[:m.end()] + lst + xml[m.end():]

def patch_rels(xml, rel_entries):
    rels = "".join(
        f'<Relationship Id="{rid}" Type="{FONT_REL_TYPE}" Target="fonts/{fn}"/>'
        for rid, fn in rel_entries)
    return xml.replace("</Relationships>", rels + "</Relationships>", 1)

def patch_content_types(xml):
    if 'Extension="fntdata"' in xml:
        return xml
    return xml.replace("</Types>",
        '<Default Extension="fntdata" ContentType="application/x-fontdata"/></Types>', 1)

def max_rid(rels_xml):
    ids = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels_xml)]
    return max(ids) if ids else 0

def embed_fonts(src, dst, font_specs):
    """font_specs: [(typeface, reg_path, bold_path_or_None), ...]. dst로 임베드본 작성."""
    with zipfile.ZipFile(src, "r") as zin:
        names = zin.namelist()
        items = {n: zin.read(n) for n in names}
        infos = {n: zin.getinfo(n) for n in names}

    rels_xml = items["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    rid = max_rid(rels_xml)
    pres_specs, rel_entries, font_blobs = [], [], []
    fi = 0
    for tf, reg_path, bold_path in font_specs:
        fi += 1; rid += 1; reg_rid = f"rId{rid}"
        reg_fn = f"font_emb_{fi}_r.fntdata"
        rel_entries.append((reg_rid, reg_fn)); font_blobs.append((reg_fn, reg_path))
        bold_rid = None
        if bold_path:
            rid += 1; bold_rid = f"rId{rid}"
            bold_fn = f"font_emb_{fi}_b.fntdata"
            rel_entries.append((bold_rid, bold_fn)); font_blobs.append((bold_fn, bold_path))
        pres_specs.append((tf, reg_rid, bold_rid))

    items["ppt/presentation.xml"] = patch_presentation(
        items["ppt/presentation.xml"].decode("utf-8"), pres_specs).encode("utf-8")
    items["ppt/_rels/presentation.xml.rels"] = patch_rels(rels_xml, rel_entries).encode("utf-8")
    items["[Content_Types].xml"] = patch_content_types(
        items["[Content_Types].xml"].decode("utf-8")).encode("utf-8")

    if os.path.exists(dst):
        os.remove(dst)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zi = zipfile.ZipInfo(n, date_time=infos[n].date_time)
            zi.compress_type = infos[n].compress_type
            zi.external_attr = infos[n].external_attr
            zout.writestr(zi, items[n])
        for fn, path in font_blobs:
            zout.writestr(f"ppt/fonts/{fn}", open(path, "rb").read())
    return [tf for tf, _, _ in font_specs]

def to_pdf(soffice, pptx, out_dir):
    profile = "/tmp/lo_profile_pptx_finalize"
    cmd = [soffice, "--headless", "--norestore",
           f"-env:UserInstallation=file://{profile}",
           "--convert-to", "pdf", "--outdir", out_dir, pptx]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = os.path.splitext(os.path.basename(pptx))[0]
    pdf = os.path.join(out_dir, base + ".pdf")
    return pdf if os.path.exists(pdf) else None

def nfc(path):
    """파일명을 NFC로 정규화. 변경 시 rename, 최종 경로 반환."""
    d, name = os.path.split(path)
    norm = unicodedata.normalize("NFC", name)
    if norm == name:
        return path
    target = os.path.join(d, norm)
    os.rename(path, target)
    return target

def verify_pdf_fonts(pdf):
    if not shutil.which("pdffonts"):
        return None
    try:
        out = subprocess.check_output(["pdffonts", pdf], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    embedded = [l.split()[0] for l in out.splitlines()[2:] if " yes " in l or l.split()[3:4] == ["yes"]]
    return out, embedded

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--soffice", default=None)
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-embed", action="store_true", help="임베드 건너뛰고 PDF만")
    args = ap.parse_args()

    src = os.path.abspath(args.input)
    if not os.path.exists(src):
        sys.exit(f"입력 없음: {src}")
    if not src.lower().endswith(".pptx"):
        sys.exit("입력은 .pptx 여야 함")
    out_dir = os.path.abspath(args.out_dir) if args.out_dir else os.path.dirname(src)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]

    log(f"[입력] {src}")
    typefaces = scan_typefaces(src)
    log(f"[스캔] 참조 typeface {len(typefaces)}종: " +
        ", ".join(f"{k}×{v}" for k, v in sorted(typefaces.items(), key=lambda x: -x[1])[:8]))

    pptx_for_pdf = src
    if not args.no_embed:
        idx = build_font_index()
        embed, skipped, missing = resolve_fonts(typefaces, idx)
        if embed:
            log("[폰트] 임베드 대상:")
            for tf, r, b in embed:
                log(f"    - {tf}: R={os.path.basename(r)} B={os.path.basename(b) if b else '없음'}")
        if skipped:
            log(f"[폰트] 범용 시스템 폰트 제외: {', '.join(skipped)}")
        if missing:
            log(f"[폰트] ⚠ 로컬 미설치 → 임베드 불가: {', '.join(missing)}")
        if not embed:
            log("[폰트] 임베드할 로컬 폰트 없음 — 임베드 단계 생략")
        else:
            dst = os.path.join(out_dir, base + "_embedded.pptx")
            embed_fonts(src, dst, embed)
            # 무결성 검증
            with zipfile.ZipFile(dst) as z:
                if z.testzip() is not None:
                    sys.exit("✗ 임베드본 zip 손상")
                pres = z.read("ppt/presentation.xml").decode()
                a, b2, c = pres.find("<p:notesSz"), pres.find("<p:embeddedFontLst"), pres.find("<p:defaultTextStyle")
                assert a < b2 < c, "embeddedFontLst 자식 순서 오류"
            dst = nfc(dst)
            log(f"[임베드] ✓ {dst} ({os.path.getsize(dst):,} bytes)")
            pptx_for_pdf = dst

    if not args.no_pdf:
        soffice = find_soffice(args.soffice)
        if not soffice:
            sys.exit("✗ LibreOffice(soffice)를 찾지 못함 — --soffice 로 경로 지정")
        pdf = to_pdf(soffice, pptx_for_pdf, out_dir)
        if not pdf:
            sys.exit("✗ PDF 변환 실패")
        # PDF는 임베드본 이름(_embedded)이 붙으므로 원래 base 이름으로 정리
        final_pdf = os.path.join(out_dir, base + ".pdf")
        if os.path.abspath(pdf) != os.path.abspath(final_pdf):
            shutil.move(pdf, final_pdf); pdf = final_pdf
        pdf = nfc(pdf)
        log(f"[PDF] ✓ {pdf} ({os.path.getsize(pdf):,} bytes)")
        vf = verify_pdf_fonts(pdf)
        if vf:
            _, embedded = vf
            log(f"[검증] PDF 임베드 폰트: {', '.join(sorted(set(embedded))) or '(파싱 실패)'}")
        else:
            log("[검증] pdffonts 미설치 — PDF 폰트 임베드 자동확인 생략")

    log("[완료]")

if __name__ == "__main__":
    main()
