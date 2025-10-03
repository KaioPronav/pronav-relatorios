# core/pdf/image_manager.py
import io
from typing import Optional
from PIL import Image, ExifTags, ImageOps

# Escolhe um filtro de reamostragem compatível com várias versões do Pillow
def _choose_resample():
    # Pillow >= 9.1: Image.Resampling exists
    resampling = getattr(Image, "Resampling", None)
    if resampling is not None:
        # prefer LANCZOS se disponível, senão BICUBIC
        return getattr(resampling, "LANCZOS", getattr(resampling, "BICUBIC", getattr(resampling, "BILINEAR", None)))
    # fallback para atributos antigos/compatíveis
    for name in ("LANCZOS", "ANTIALIAS", "BICUBIC", "BILINEAR"):
        val = getattr(Image, name, None)
        if val is not None:
            return val
    # último recurso
    return getattr(Image, "NEAREST", 0)

LANCZOS = _choose_resample()


def _orient_image_by_exif(img: Image.Image) -> Image.Image:
    """
    Aplica orientação EXIF se existir. Faz checagens de tipo para agradar ao Pylance.
    """
    try:
        getexif = getattr(img, "_getexif", None)
        exif = None
        if callable(getexif):
            try:
                exif = getexif()
            except Exception:
                exif = None

        if isinstance(exif, dict) and exif:
            # achar o tag number da Orientation com segurança
            orientation_tag = None
            # ExifTags.TAGS é mapping name->number; queremos number por nome
            for tag_num, tag_name in ExifTags.TAGS.items():
                if tag_name == "Orientation":
                    orientation_tag = tag_num
                    break
            if orientation_tag is not None and orientation_tag in exif:
                orient = exif.get(orientation_tag)
                # aplicar transformações conhecidas
                if orient == 2:
                    img = ImageOps.mirror(img)
                elif orient == 3:
                    img = img.rotate(180, expand=True)
                elif orient == 4:
                    img = ImageOps.flip(img)
                elif orient == 5:
                    img = ImageOps.mirror(img.rotate(-90, expand=True))
                elif orient == 6:
                    img = img.rotate(-90, expand=True)
                elif orient == 7:
                    img = ImageOps.mirror(img.rotate(90, expand=True))
                elif orient == 8:
                    img = img.rotate(90, expand=True)
    except Exception:
        # best-effort: se algo falhar, retornamos a imagem inalterada
        return img
    return img


def is_landscape_image_bytes(b: bytes) -> bool:
    """
    Retorna True se a imagem (bytes) for paisagem. Safe: retorna False em falha.
    """
    if not b:
        return False
    try:
        with Image.open(io.BytesIO(b)) as img:
            img = _orient_image_by_exif(img)
            w, h = img.size
            return w >= h
    except Exception:
        return False


def compress_image_bytes(
    b: bytes,
    max_bytes: int = 400000,
    max_width_px: int = 1800,
    max_height_px: int = 1800,
    initial_quality: int = 85
) -> bytes:
    """
    Compacta a imagem (bytes) tentando ficar abaixo de max_bytes.
    Estratégia:
     - aplica EXIF orientation
     - redimensiona mantendo proporção se passa dos limites
     - tenta salvar em JPEG (convertendo alpha para fundo branco se necessário)
     - reduz qualidade em passos; se necessário reduz dimensão progressivamente
     - em último caso devolve os bytes originais
    """
    if not b:
        return b
    try:
        with Image.open(io.BytesIO(b)) as img:
            img = _orient_image_by_exif(img)

            # resize se precisar
            w, h = img.size
            ratio = min(1.0, float(max_width_px) / max(1, w), float(max_height_px) / max(1, h))
            if ratio < 1.0:
                new_w = max(1, int(w * ratio))
                new_h = max(1, int(h * ratio))
                img = img.resize((new_w, new_h), resample=LANCZOS)

            # tratar alpha: compor em fundo branco se necessário
            has_alpha = (img.mode in ("RGBA", "LA")) or (img.mode == "P" and "transparency" in img.info)
            if has_alpha:
                bg = Image.new("RGB", img.size, (255, 255, 255))
                rgba = img.convert("RGBA")
                alpha = rgba.split()[-1]
                bg.paste(rgba.convert("RGB"), mask=alpha)
                working = bg
            else:
                if img.mode != "RGB":
                    try:
                        working = img.convert("RGB")
                    except Exception:
                        working = img.copy()
                else:
                    working = img

            out = io.BytesIO()
            quality = int(max(30, min(95, initial_quality)))
            last_attempt = None

            # várias tentativas diminuindo qualidade
            for _ in range(6):
                out.seek(0); out.truncate(0)
                try:
                    working.save(out, format="JPEG", quality=quality, optimize=True)
                except OSError:
                    # optimize pode falhar; tentar sem
                    working.save(out, format="JPEG", quality=quality)
                data = out.getvalue()
                if len(data) <= max_bytes:
                    return data
                last_attempt = data
                quality = max(30, int(quality * 0.7))

            # se ainda grande, reduzir dimensão progressivamente
            if last_attempt and len(last_attempt) > max_bytes:
                cur = working
                while len(last_attempt) > max_bytes:
                    cw, ch = cur.size
                    if cw <= 100 or ch <= 100:
                        break
                    new_w = max(1, int(cw * 0.9))
                    new_h = max(1, int(ch * 0.9))
                    cur = cur.resize((new_w, new_h), resample=LANCZOS)
                    out.seek(0); out.truncate(0)
                    try:
                        cur.save(out, format="JPEG", quality=max(30, quality), optimize=True)
                    except OSError:
                        cur.save(out, format="JPEG", quality=max(30, quality))
                    last_attempt = out.getvalue()
                    if len(last_attempt) <= max_bytes:
                        return last_attempt

            return last_attempt or b
    except Exception:
        return b
