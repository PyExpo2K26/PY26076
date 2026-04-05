from PIL import Image

def convert_png_to_ico(png_path, ico_path):
    img = Image.open(png_path)
    # Ensure image is in RGBA mode for transparency matching
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    # Save as ICO, including multiple sizes
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])

if __name__ == "__main__":
    convert_png_to_ico(
        r"C:\Users\KiTE\.gemini\antigravity\brain\bcf82ee2-f45c-41bd-b0a7-d1284c1eaf86\infinity_icon_1775379406223.png",
        "infini_think.ico"
    )
