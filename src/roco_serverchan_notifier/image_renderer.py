"""Pillow-based image renderer for merchant notification cards.

Generates PNG images directly from product data without requiring
a browser engine (Playwright/Chromium). Produces warm-themed card
images matching the 洛克王国 visual style.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Assets directory (bundled in the package)
_ASSETS_DIR = Path(__file__).parent / "assets"

# --- Color palette (warm game theme) ---
BG_COLOR = (236, 227, 211)
HEADER_BG = (245, 236, 221)
CARD_BG = (255, 252, 247)
TEXT_PRIMARY = (51, 39, 25)
TEXT_SECONDARY = (107, 88, 70)
ACCENT = (160, 99, 29)
TAG_BG = (255, 214, 153, 100)
TAG_TEXT = (154, 95, 25)
BORDER_COLOR = (118, 97, 74, 36)
WHITE = (255, 255, 255)

# --- Layout constants ---
CANVAS_WIDTH = 820
PADDING = 18
CARD_RADIUS = 22
HEADER_HEIGHT = 130
PRODUCT_CARD_HEIGHT = 120
PRODUCT_CARD_HEIGHT_WITH_PRICE = 160
PRODUCT_IMG_SIZE = 92
FOOTER_HEIGHT = 50


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Load the bundled Chinese font."""
    font_path = _ASSETS_DIR / "fzlant.ttf"
    try:
        return ImageFont.truetype(str(font_path), size)
    except Exception:
        logger.warning("Failed to load bundled font, falling back to default")
        return ImageFont.load_default()


def _rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: tuple | None = None,
    outline: tuple | None = None,
    width: int = 1,
):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _truncate_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate text with ellipsis if it exceeds max_width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    while len(text) > 1:
        text = text[:-1]
        bbox = draw.textbbox((0, 0), text + "...", font=font)
        if bbox[2] - bbox[0] <= max_width:
            return text + "..."
    return text


def _load_product_image(url: str, size: int = PRODUCT_IMG_SIZE) -> Image.Image | None:
    """Download and resize a product image. Returns None on failure."""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        return img
    except Exception as exc:
        logger.debug("Failed to load product image from %s: %s", url, exc)
        return None


def _load_asset_image(name: str) -> Image.Image | None:
    """Load an image from the assets directory."""
    path = _ASSETS_DIR / name
    if path.exists():
        try:
            return Image.open(str(path)).convert("RGBA")
        except Exception:
            return None
    return None


def render_merchant_card(processed: dict[str, Any]) -> bytes:
    """Render a merchant card image from processed data.

    Args:
        processed: Processed merchant data dict containing:
            - title: str
            - subtitle: str
            - product_count: int
            - round_info: dict (current, total, countdown)
            - products: list[dict] (name, image, time_label, price, buy_limit_num)

    Returns:
        PNG image bytes.

    Raises:
        Exception: If rendering fails (caller should catch and fall back to text).
    """
    products = processed.get("products") or []
    round_info = processed.get("round_info") or {}
    title = processed.get("title", "远行商人")
    subtitle = processed.get("subtitle", "")
    product_count = processed.get("product_count", len(products))

    # --- Load fonts ---
    font_title = _load_font(36)
    font_subtitle = _load_font(16)
    font_product_name = _load_font(24)
    font_small = _load_font(15)
    font_medium = _load_font(17)
    font_count_num = _load_font(26)
    font_round = _load_font(15)

    # --- Calculate total image height ---
    height = PADDING + HEADER_HEIGHT + PADDING

    if products:
        for p in products:
            has_price = p.get("price") is not None or p.get("buy_limit_num") is not None
            height += (PRODUCT_CARD_HEIGHT_WITH_PRICE if has_price else PRODUCT_CARD_HEIGHT) + 12
    else:
        height += 80

    height += PADDING + FOOTER_HEIGHT + PADDING

    # --- Create image ---
    img = Image.new("RGB", (CANVAS_WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = PADDING

    # --- Header card ---
    _rounded_rectangle(
        draw,
        (PADDING, y, CANVAS_WIDTH - PADDING, y + HEADER_HEIGHT),
        radius=24,
        fill=HEADER_BG,
        outline=(118, 97, 74, 56),
        width=1,
    )

    # Title badge
    badge_img = _load_asset_image("yuanxingshangren.png")
    badge_x = PADDING + 24
    badge_y = y + (HEADER_HEIGHT - 60) // 2
    if badge_img:
        badge_resized = badge_img.resize((60, 60), Image.Resampling.LANCZOS)
        img.paste(badge_resized, (badge_x, badge_y), badge_resized if badge_resized.mode == "RGBA" else None)
    else:
        # Text fallback
        _rounded_rectangle(draw, (badge_x, badge_y, badge_x + 60, badge_y + 60), radius=12, fill=ACCENT)
        bbox = draw.textbbox((0, 0), title[:1], font=font_title)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((badge_x + (60 - tw) // 2, badge_y + (60 - th) // 2), title[:1], fill=WHITE, font=font_title)

    # Title text
    title_x = badge_x + 60 + 14
    title_y = y + 28
    draw.text((title_x, title_y), title, fill=TEXT_PRIMARY, font=font_title)
    if subtitle:
        draw.text((title_x, title_y + 44), subtitle, fill=TEXT_SECONDARY, font=font_subtitle)

    # Product count chip (right side)
    count_text = f"商品数 {product_count}"
    count_bbox = draw.textbbox((0, 0), count_text, font=font_medium)
    count_tw = count_bbox[2] - count_bbox[0]
    chip_w = count_tw + 32
    chip_x = CANVAS_WIDTH - PADDING - 24 - chip_w
    chip_y = y + 20
    _rounded_rectangle(
        draw,
        (chip_x, chip_y, chip_x + chip_w, chip_y + 38),
        radius=19,
        fill=WHITE,
    )
    draw.text((chip_x + 16, chip_y + 8), count_text, fill=TEXT_SECONDARY, font=font_medium)

    # Round info
    round_text = f"第 {round_info.get('current', '--')}/{round_info.get('total', '--')} 轮"
    countdown_text = f"剩余 {round_info.get('countdown', '--')}"

    pill_y = y + HEADER_HEIGHT - 42
    # Round pill
    rbbox = draw.textbbox((0, 0), round_text, font=font_round)
    rtw = rbbox[2] - rbbox[0]
    rp_x = CANVAS_WIDTH - PADDING - 24 - rtw - 28
    _rounded_rectangle(draw, (rp_x, pill_y, rp_x + rtw + 28, pill_y + 28), radius=14, fill=WHITE)
    draw.text((rp_x + 14, pill_y + 4), round_text, fill=TEXT_SECONDARY, font=font_round)

    # Countdown pill
    cbbox = draw.textbbox((0, 0), countdown_text, font=font_round)
    ctw = cbbox[2] - cbbox[0]
    cp_x = rp_x - ctw - 42
    _rounded_rectangle(draw, (cp_x, pill_y, cp_x + ctw + 28, pill_y + 28), radius=14, fill=WHITE)
    draw.text((cp_x + 14, pill_y + 4), countdown_text, fill=(191, 95, 63), font=font_round)

    y += HEADER_HEIGHT + PADDING

    # --- Product cards ---
    if products:
        for product in products:
            name = product.get("name", "未知")
            time_label = product.get("time_label", "--:--")
            price = product.get("price")
            buy_limit = product.get("buy_limit_num")
            image_url = product.get("image", "")

            has_price = price is not None or buy_limit is not None
            card_h = PRODUCT_CARD_HEIGHT_WITH_PRICE if has_price else PRODUCT_CARD_HEIGHT

            # Card background
            _rounded_rectangle(
                draw,
                (PADDING, y, CANVAS_WIDTH - PADDING, y + card_h),
                radius=CARD_RADIUS,
                fill=CARD_BG,
                outline=BORDER_COLOR[:3],
                width=1,
            )

            # Product image
            prod_img = _load_product_image(image_url)
            img_x = PADDING + 16
            img_y = y + (card_h - PRODUCT_IMG_SIZE) // 2
            if prod_img:
                img.paste(prod_img, (img_x, img_y), prod_img if prod_img.mode == "RGBA" else None)
            else:
                # Placeholder circle
                _rounded_rectangle(
                    draw,
                    (img_x, img_y, img_x + PRODUCT_IMG_SIZE, img_y + PRODUCT_IMG_SIZE),
                    radius=16,
                    fill=(239, 228, 210),
                )
                ph_text = name[:1] if name else "?"
                ph_bbox = draw.textbbox((0, 0), ph_text, font=font_product_name)
                ph_tw = ph_bbox[2] - ph_bbox[0]
                ph_th = ph_bbox[3] - ph_bbox[1]
                draw.text(
                    (img_x + (PRODUCT_IMG_SIZE - ph_tw) // 2, img_y + (PRODUCT_IMG_SIZE - ph_th) // 2),
                    ph_text,
                    fill=TEXT_SECONDARY,
                    font=font_product_name,
                )

            # Product name
            name_x = img_x + PRODUCT_IMG_SIZE + 16
            name_y = y + 18
            display_name = _truncate_text(draw, name, font_product_name, CANVAS_WIDTH - name_x - 180)
            draw.text((name_x, name_y), display_name, fill=TEXT_PRIMARY, font=font_product_name)

            # Time label tag
            tag_y = name_y + 36
            time_text = f"北京时间 {time_label}"
            tbbox = draw.textbbox((0, 0), time_text, font=font_small)
            ttw = tbbox[2] - tbbox[0]
            # Tag background (semi-transparent simulation)
            tag_overlay = Image.new("RGBA", (ttw + 24, 28), (255, 214, 153, 100))
            tag_mask = Image.new("L", (ttw + 24, 28), 0)
            tag_draw = ImageDraw.Draw(tag_mask)
            _rounded_rectangle(tag_draw, (0, 0, ttw + 24, 28), radius=14, fill=255)
            img.paste(
                Image.new("RGB", (ttw + 24, 28), (255, 214, 153)),
                (name_x, tag_y),
                tag_mask,
            )
            draw.text((name_x + 12, tag_y + 4), time_text, fill=TAG_TEXT, font=font_small)

            # Price / limit info (right column)
            if has_price:
                right_x = CANVAS_WIDTH - PADDING - 130
                center_y = y + card_h // 2

                # Coin icon
                coin_img = _load_asset_image("coin.png")
                if coin_img and price is not None:
                    coin_resized = coin_img.resize((20, 20), Image.Resampling.LANCZOS)
                    price_text = str(price)
                    pbbox = draw.textbbox((0, 0), price_text, font=font_medium)
                    ptw = pbbox[2] - pbbox[0]
                    total_w = 20 + 6 + ptw
                    cx = right_x + (120 - total_w) // 2
                    img.paste(coin_resized, (cx, center_y - 22), coin_resized if coin_resized.mode == "RGBA" else None)
                    draw.text((cx + 26, center_y - 20), price_text, fill=(139, 94, 43), font=font_medium)
                elif price is not None:
                    price_text = f"{price} 洛克贝"
                    pbbox = draw.textbbox((0, 0), price_text, font=font_medium)
                    ptw = pbbox[2] - pbbox[0]
                    draw.text((right_x + (120 - ptw) // 2, center_y - 22), price_text, fill=(139, 94, 43), font=font_medium)

                if buy_limit is not None:
                    limit_text = f"限购 {buy_limit}"
                    lbbox = draw.textbbox((0, 0), limit_text, font=font_small)
                    ltw = lbbox[2] - lbbox[0]
                    draw.text(
                        (right_x + (120 - ltw) // 2, center_y + 6),
                        limit_text,
                        fill=TEXT_SECONDARY,
                        font=font_small,
                    )
            else:
                # No price info - show a subtle dash
                right_x = CANVAS_WIDTH - PADDING - 130
                draw.text(
                    (right_x + 55, y + card_h // 2 - 10),
                    "-",
                    fill=(180, 170, 155),
                    font=font_medium,
                )

            y += card_h + 12
    else:
        # Empty state
        _rounded_rectangle(
            draw,
            (PADDING, y, CANVAS_WIDTH - PADDING, y + 70),
            radius=CARD_RADIUS,
            fill=CARD_BG,
            outline=(120, 102, 81, 90),
            width=1,
        )
        empty_text = "本轮暂无商品，稍后再来看看。"
        ebbox = draw.textbbox((0, 0), empty_text, font=font_medium)
        etw = ebbox[2] - ebbox[0]
        draw.text(
            ((CANVAS_WIDTH - etw) // 2, y + 24),
            empty_text,
            fill=TEXT_SECONDARY,
            font=font_medium,
        )
        y += 80

    # --- Footer ---
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone(timedelta(hours=8)))
    footer_text = f"生成时间: {now.strftime('%Y-%m-%d %H:%M')}"
    fbbox = draw.textbbox((0, 0), footer_text, font=font_small)
    ftw = fbbox[2] - fbbox[0]
    draw.text(((CANVAS_WIDTH - ftw) // 2, y + 10), footer_text, fill=TEXT_SECONDARY, font=font_small)

    # --- Export ---
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
