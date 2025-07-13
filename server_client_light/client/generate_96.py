from PIL import Image, ImageDraw, ImageFont

# Crea un’immagine 96×96 px, sfondo azzurro
img = Image.new("RGB", (96, 96), color=(173, 216, 230))
draw = ImageDraw.Draw(img)
img.save("dog.png")
print("Salvato dog.png")

